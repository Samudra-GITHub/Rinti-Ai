"""Repeatable benchmark for Rinti-AI models.

Runs the same cases, with the same production system prompt and generation
settings, against each target (a provider plus a model) and records
correctness, instruction following, response style, timing and memory. It
calls the provider layer directly, so "which provider answered" is true by
construction, and it needs no external evaluation service: every check is
automated (including running generated Python code in a subprocess).

Usage (from backend/, with the virtualenv active):

    python scripts/benchmark.py --targets ollama:qwen2.5:7b,groq:openai/gpt-oss-120b
    python scripts/benchmark.py --targets ollama:phi4-mini --runs 2 --only arithmetic,table
    python scripts/benchmark.py --list

A target is "<provider>:<model>". Results are written to docs/benchmarks/ as
JSON (every raw response) and Markdown (the summary).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from core.context import fit_messages  # noqa: E402
from core.personality import RINTI_SYSTEM_PROMPT  # noqa: E402
from providers.base import GenParams, ProviderError  # noqa: E402
from providers.registry import get_provider  # noqa: E402

TEMPERATURE = 0.7  # what the app uses
MAX_TOKENS = 1200


# ---------------------------------------------------------------------------
# Style analysis (shared by every case)
# ---------------------------------------------------------------------------

_PREAMBLE = re.compile(r"^\s*(certainly|sure[,!]|of course|absolutely|great question|here(?:'s| is) a (?:comprehensive|detailed))", re.I)
_CLOSING = re.compile(
    r"(feel free to ask|let me know if|hope this helps|if you(?:'d| would)? (?:like|want|have|need)[^.\n]{0,60}(?:more|further|anything)|don't hesitate)",
    re.I,
)


def style(text: str) -> Dict[str, Any]:
    lines = text.strip().splitlines()
    return {
        "words": len(text.split()),
        "paragraphs": len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]),
        "headings": sum(1 for l in lines if re.match(r"\s{0,3}#{1,6}\s", l)),
        "bullets": sum(1 for l in lines if re.match(r"\s*([-*•]|\d+[.)])\s", l)),
        "table": bool(re.search(r"^\s*\|.*\|\s*$\n^\s*\|?\s*:?-{3,}", text, re.M)),
        "bold": len(re.findall(r"\*\*[^*]+\*\*", text)),
        "preamble": bool(_PREAMBLE.search(text)),
        "closing_filler": bool(_CLOSING.search(text[-300:])),
        "odd_chars": sorted({hex(ord(c)) for c in text if c in "‑  ​⁠﻿"}),
    }


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

Check = Tuple[str, str, bool]  # (category, name, passed)


@dataclass
class Case:
    id: str
    title: str
    messages: List[Dict[str, str]]  # without the system prompt
    check: Callable[[str, Dict[str, Any]], List[Check]]
    max_tokens: int = MAX_TOKENS
    json_mode: bool = False


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def c_factual(text, s):
    return [
        ("correctness", "mentions the Pandavas/Kauravas or Kurukshetra", _has(text, r"pandava", r"kaurava", r"kurukshetra")),
        ("correctness", "mentions Sanskrit epic / ancient India", _has(text, r"epic", r"ancient india")),
        ("style", "concise (<= 170 words)", s["words"] <= 170),
        ("style", "no table", not s["table"]),
        ("style", "no headings", s["headings"] == 0),
        ("style", "at most 2 bold phrases", s["bold"] <= 2),
        ("style", "no generic preamble", not s["preamble"]),
        ("style", "no generic closing line", not s["closing_filler"]),
    ]


def c_detailed(text, s):
    return [
        ("correctness", "covers dharma", _has(text, r"dharma")),
        ("correctness", "covers karma or detachment", _has(text, r"karma", r"detach", r"nishkama")),
        ("instruction", "detailed (>= 250 words)", s["words"] >= 250),
        ("style", "no generic preamble", not s["preamble"]),
        ("style", "no generic closing line", not s["closing_filler"]),
        ("style", "not wall of bullets (bullets <= 12)", s["bullets"] <= 12),
    ]


def c_arith(text, s):
    return [
        ("correctness", "answer is 408", "408" in text.replace(",", "")),
        ("instruction", "direct (<= 25 words)", s["words"] <= 25),
        ("style", "no headings or table", s["headings"] == 0 and not s["table"]),
    ]


def c_reasoning(text, s):
    return [
        ("correctness", "change is $6.50", _has(text, r"6\.50", r"6\.5\b")),
        ("style", "no generic closing line", not s["closing_filler"]),
        ("style", "no table", not s["table"]),
    ]


def c_conversational(text, s):
    return [
        ("instruction", "short, human reply (<= 120 words)", s["words"] <= 120),
        ("style", "no headings", s["headings"] == 0),
        ("style", "no bullet list", s["bullets"] == 0),
        ("style", "no table", not s["table"]),
        ("style", "no generic preamble", not s["preamble"]),
        ("style", "responds to the feeling", _has(text, r"overwhelm", r"sounds", r"that's|that is", r"understand", r"hard|tough|heavy|a lot")),
    ]


def c_table(text, s):
    return [
        ("instruction", "contains a table", s["table"]),
        ("correctness", "mentions both groups", _has(text, r"pandava") and _has(text, r"kaurava")),
        ("correctness", "table has at least 3 rows", len(re.findall(r"^\s*\|.*\|\s*$", text, re.M)) >= 5),
    ]


_ARJUNA_Q = "Tell me about Arjuna in two sentences."
_ARJUNA_A = (
    "Arjuna is one of the five Pandava brothers and the greatest archer of his age. "
    "He is the warrior to whom Krishna delivers the Bhagavad Gita on the field of Kurukshetra."
)


def c_followup(text, s):
    return [
        ("correctness", "resolves 'his' to Arjuna's doubt about fighting kin/teachers", _has(text, r"kin\b", r"relatives", r"teachers?", r"family", r"cousins", r"elders", r"killing", r"fight")),
        ("correctness", "ties it to duty/dharma or the Gita", _has(text, r"dharma", r"duty", r"gita", r"krishna")),
        ("style", "no generic closing line", not s["closing_filler"]),
    ]


def _run_python(code: str, call: str) -> Tuple[bool, str]:
    """Runs generated code plus a call in an isolated subprocess (no stdin, 8 s limit)."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(code + "\n\n" + call + "\n")
        path = handle.name
    try:
        out = subprocess.run([sys.executable, "-I", path], capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL)
        return out.returncode == 0, (out.stdout + out.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        os.unlink(path)


def c_code(text, s):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S | re.I)
    code = max(blocks, key=len) if blocks else ""
    name_match = re.search(r"def\s+(\w+)\s*\(", code)
    works = False
    if name_match:
        ok, output = _run_python(
            code,
            f"result = {name_match.group(1)}([3, 1, 3, 2, 1, 4, 2])\nassert list(result) == [3, 1, 2, 4], result\nprint('ok')",
        )
        works = ok and "ok" in output
    return [
        ("instruction", "returns a fenced code block", bool(blocks)),
        ("correctness", "generated function runs and is correct", works),
    ]


def c_debug(text, s):
    return [
        ("correctness", "identifies mutating a list while iterating", _has(text, r"iterat", r"while looping", r"modif", r"mutat")),
        ("correctness", "explains skipped elements/indexes", _has(text, r"skip", r"index", r"shift", r"miss")),
        ("instruction", "offers a fix in a code block", "```" in text),
    ]


def c_ambiguous(text, s):
    return [
        ("instruction", "asks for the missing information", "?" in text and _has(text, r"what|which|share|provide|could you|can you|paste|more (?:detail|context)")),
        ("instruction", "does not invent code or a fix", "```" not in text),
        ("style", "short (<= 60 words)", s["words"] <= 60),
    ]


def c_unknown(text, s):
    admits = _has(text, r"don't (?:have|know)", r"do not (?:have|know)", r"haven't (?:told|shared|mentioned)", r"no (?:record|information|way)",
                  r"not sure", r"can't (?:know|tell|see)", r"cannot (?:know|tell|see)", r"i'm not aware", r"you haven't", r"unable to")
    return [
        ("correctness", "admits it does not know instead of inventing a name", admits),
        ("style", "short (<= 50 words)", s["words"] <= 50),
    ]


def _filler_history() -> List[Dict[str, str]]:
    topics = [
        ("the water cycle", "Water evaporates, condenses into clouds, and returns as rain or snow."),
        ("how bicycles stay upright", "Steering corrections and forward motion keep the rider balanced."),
        ("why the sky is blue", "Shorter blue wavelengths scatter more in the atmosphere."),
        ("what a prime number is", "A number greater than one with no divisors except one and itself."),
        ("how bread rises", "Yeast produces gas that is trapped in the dough as it ferments."),
        ("what causes tides", "The Moon's gravity pulls on the oceans, raising bulges of water."),
    ]
    turns: List[Dict[str, str]] = [
        {"role": "user", "content": "Before we start: my favourite number is 73, remember that."},
        {"role": "assistant", "content": "Noted, your favourite number is 73."},
    ]
    for i in range(14):
        topic, answer = topics[i % len(topics)]
        turns.append({"role": "user", "content": f"Quick question {i + 1}: can you explain {topic}?"})
        turns.append({"role": "assistant", "content": f"{answer} " + "It is a good example of an everyday process with a clear cause. " * 6})
    return turns


def c_long(text, s):
    return [
        ("correctness", "recalls the number 73 from the start of a long chat", "73" in text),
        ("instruction", "short answer (<= 40 words)", s["words"] <= 40),
    ]


_FIXTURE_SOURCES = (
    "[1] Solid-state battery progress report — example-energy.test\n"
    "Company A began pilot production of solid-state cells reaching 400 Wh/kg in 2026.\n\n"
    "[2] Market outlook — example-research.test\n"
    "Analysts expect solid-state batteries to reach under 2 percent of EV sales by 2030."
)


def c_research_json(text, s):
    try:
        payload = json.loads(text)
        valid = isinstance(payload, dict) and str(payload.get("intent", "")).upper() in {
            "NO_RESEARCH", "CURRENT_INFORMATION", "FACT_CHECK", "COMPARISON", "PRODUCT_RESEARCH", "NEWS_RESEARCH", "GENERAL_RESEARCH",
        }
        needs = str(payload.get("intent", "")).upper() != "NO_RESEARCH"
    except ValueError:
        valid, needs = False, False
    return [
        ("instruction", "returns valid JSON with a known intent", valid),
        ("correctness", "recognises a 'latest developments' question needs research", needs),
    ]


def c_research_synthesis(text, s):
    from research.synthesis import parse_structured_answer

    try:
        answer, notes = parse_structured_answer(text, "latest solid-state battery news")
        parsed = not notes and bool(answer.overview)
        flat = json.dumps(
            {"o": answer.overview, "s": answer.executive_summary, "x": [sec.content or sec.items for sec in answer.sections]},
            default=str,
        )
    except Exception:  # noqa: BLE001
        parsed, flat = False, ""
    used = {int(n) for n in re.findall(r"\[(\d+)\]", flat)}
    return [
        ("instruction", "returns the structured JSON answer", parsed),
        ("correctness", "cites sources", bool(used)),
        ("correctness", "cites only the 2 real sources", used <= {1, 2}),
        ("correctness", "uses the evidence (400 Wh/kg or 2 percent)", _has(flat, r"400", r"2 percent|2%")),
    ]


def build_cases() -> List[Case]:
    from research.intent import _CLASSIFIER_PROMPT
    from research.synthesis import build_synthesis_prompt

    cases = [
        Case("factual", "Simple factual question", [{"role": "user", "content": "What is the Mahabharata?"}], c_factual),
        Case("detailed", "Detailed explanation", [{"role": "user", "content": "Explain the Mahabharata's major philosophical themes in detail."}], c_detailed, max_tokens=1500),
        Case("arithmetic", "Arithmetic", [{"role": "user", "content": "What's 17 multiplied by 24?"}], c_arith),
        Case("reasoning", "Basic reasoning", [{"role": "user", "content": "I buy 3 notebooks at $4.50 each and pay with a $20 bill. How much change do I get?"}], c_reasoning),
        Case("conversational", "Natural conversation", [{"role": "user", "content": "I'm feeling a bit overwhelmed with work today."}], c_conversational),
        Case("table", "Explicit table request", [{"role": "user", "content": "Compare the Pandavas and Kauravas in a table."}], c_table),
        Case(
            "followup", "Follow-up needing context",
            [
                {"role": "user", "content": _ARJUNA_Q},
                {"role": "assistant", "content": _ARJUNA_A},
                {"role": "user", "content": "And what was his main doubt before the war?"},
            ],
            c_followup,
        ),
        Case("code", "Coding task (code is executed)", [{"role": "user", "content": "Write a Python function that removes duplicates from a list while keeping the original order."}], c_code),
        Case(
            "debug", "Debugging task",
            [{"role": "user", "content": "Why does this skip elements?\n\n```python\nnums = [1, 2, 4, 3]\nfor n in nums:\n    if n % 2 == 0:\n        nums.remove(n)\nprint(nums)\n```"}],
            c_debug,
        ),
        Case("long", "Long conversation (recall)", _filler_history() + [{"role": "user", "content": "Earlier I told you a number. What was it?"}], c_long),
        Case("unknown_fact", "Unknown personal fact (must not invent)", [{"role": "user", "content": "What is my pet's name?"}], c_unknown),
        Case("ambiguous", "Ambiguous request", [{"role": "user", "content": "Fix it."}], c_ambiguous),
        Case(
            "research_intent", "Research integration: intent classification (JSON)",
            [{"role": "user", "content": _CLASSIFIER_PROMPT.format(today=datetime.now().strftime("%Y-%m-%d"), query="What are the latest developments in solid-state batteries?")}],
            c_research_json, max_tokens=200, json_mode=True,
        ),
        Case(
            "research_synthesis", "Research integration: cited synthesis (JSON)",
            [{"role": "user", "content": build_synthesis_prompt("What is the latest on solid-state batteries?", _FIXTURE_SOURCES)}],
            c_research_synthesis, max_tokens=1500, json_mode=True,
        ),
    ]
    return cases


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def ollama_memory(base_url: str) -> Optional[Dict[str, float]]:
    try:
        data = json.loads(urllib.request.urlopen(f"{base_url}/api/ps", timeout=3).read())
        models = data.get("models", [])
        if not models:
            return None
        return {
            "model_gb": round(sum(m.get("size", 0) for m in models) / 1e9, 2),
            "gpu_gb": round(sum(m.get("size_vram", 0) for m in models) / 1e9, 2),
        }
    except Exception:  # noqa: BLE001
        return None


def gpu_used_mb() -> Optional[int]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return int(out.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


def unload_ollama_models(base_url: str, except_model: Optional[str] = None) -> None:
    try:
        data = json.loads(urllib.request.urlopen(f"{base_url}/api/ps", timeout=3).read())
        for item in data.get("models", []):
            name = item.get("name")
            if name and name != except_model:
                body = json.dumps({"model": name, "keep_alive": 0}).encode()
                urllib.request.urlopen(urllib.request.Request(f"{base_url}/api/generate", data=body), timeout=10).read()
    except Exception:  # noqa: BLE001
        pass


@dataclass
class Result:
    case: str
    target: str
    provider: str
    model: str
    ok: bool
    error: str = ""
    text: str = ""
    ttft: Optional[float] = None
    total: Optional[float] = None
    tokens: Optional[int] = None
    tokens_per_s: Optional[float] = None
    dropped_messages: int = 0
    style: Dict[str, Any] = field(default_factory=dict)
    checks: List[Dict[str, Any]] = field(default_factory=list)
    memory: Optional[Dict[str, float]] = None
    gpu_used_mb: Optional[int] = None


async def run_case(provider_name: str, model: str, case: Case) -> Result:
    provider = get_provider(provider_name)
    target = f"{provider_name}:{model}"
    messages = [{"role": "system", "content": RINTI_SYSTEM_PROMPT}] + case.messages
    params = GenParams(
        temperature=TEMPERATURE,
        max_tokens=case.max_tokens,
        json_mode=case.json_mode,
        num_ctx=settings.local_num_ctx if provider.kind == "local" else None,
    )
    fitted, dropped = fit_messages(messages, provider.context_limit(model), params.max_tokens or 1024)
    result = Result(case.id, target, provider_name, model, ok=False, dropped_messages=dropped)

    started = time.perf_counter()
    first: Optional[float] = None
    parts: List[str] = []
    usage: Dict[str, Any] = {}
    try:
        async with asyncio.timeout(settings.request_timeout_seconds):
            async for event in provider.stream(fitted, model, params):
                if event.kind == "text":
                    if first is None:
                        first = time.perf_counter() - started
                    parts.append(event.text)
                elif event.kind == "usage":
                    usage = event.usage
        result.ok = True
    except ProviderError as exc:
        result.error = f"{exc.code}: {exc.user_message}"
    except TimeoutError:
        result.error = "timeout"
    total = time.perf_counter() - started

    text = "".join(parts)
    result.text, result.ttft, result.total = text, first, round(total, 2)
    if first is not None:
        result.ttft = round(first, 2)
    tokens = usage.get("completion_tokens") or (max(1, len(text) // 4) if text else 0)
    result.tokens = tokens
    if first is not None and tokens and total - first > 0.2:
        result.tokens_per_s = round(tokens / (total - first), 1)
    if provider_name == "ollama":
        result.memory = ollama_memory(settings.ollama_base_url)
        result.gpu_used_mb = gpu_used_mb()
    if result.ok and text.strip():
        result.style = style(text)
        result.checks = [{"category": c, "name": n, "passed": bool(p)} for c, n, p in case.check(text, result.style)]
    elif result.ok:
        result.ok = False
        result.error = "empty response"
    return result


async def warm_up(provider_name: str, model: str) -> Optional[float]:
    """Loads a local model (or opens a cloud connection) so timing excludes the one-off load."""
    provider = get_provider(provider_name)
    started = time.perf_counter()
    params = GenParams(temperature=0, max_tokens=4, num_ctx=settings.local_num_ctx if provider.kind == "local" else None)
    try:
        async for _ in provider.stream([{"role": "user", "content": "Reply with the word ready."}], model, params):
            pass
    except ProviderError:
        return None
    return round(time.perf_counter() - started, 1)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def summarize(results: List[Result], targets: List[str], cold: Dict[str, Optional[float]]) -> str:
    lines: List[str] = []
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines += [f"# Rinti-AI model benchmark ({stamp})", ""]
    lines += [
        f"Same production system prompt, temperature {TEMPERATURE}, same cases for every target. "
        f"Local context window: {settings.local_num_ctx} tokens. Checks are automated (see `scripts/benchmark.py`).",
        "",
        "## Summary",
        "",
        "| Target | Failures | Correctness | Instruction | Style | Median 1st token | Median total | Tokens/s | Model memory (GPU) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for target in targets:
        mine = [r for r in results if r.target == target]
        fails = sum(1 for r in mine if not r.ok)

        def tally(cat: str) -> str:
            checks = [c for r in mine for c in r.checks if c["category"] == cat]
            return f"{sum(c['passed'] for c in checks)}/{len(checks)}" if checks else "n/a"

        ttfts = [r.ttft for r in mine if r.ttft is not None]
        totals = [r.total for r in mine if r.total is not None and r.ok]
        speeds = [r.tokens_per_s for r in mine if r.tokens_per_s]
        mems = [r.memory for r in mine if r.memory]
        mem = f"{max(m['model_gb'] for m in mems):.1f} GB ({max(m['gpu_gb'] for m in mems):.1f})" if mems else "cloud"
        lines.append(
            f"| `{target}` | {fails}/{len(mine)} | {tally('correctness')} | {tally('instruction')} | {tally('style')} | "
            f"{statistics.median(ttfts):.1f}s | {statistics.median(totals):.1f}s | "
            f"{statistics.median(speeds) if speeds else 0:.0f} | {mem} |"
            if ttfts and totals else f"| `{target}` | {fails}/{len(mine)} | - | - | - | - | - | - | {mem} |"
        )
    if any(v is not None for v in cold.values()):
        lines += ["", "Cold start (first request after load/connect): " + ", ".join(f"`{t}` {v}s" for t, v in cold.items() if v is not None)]

    lines += ["", "## Per case", ""]
    case_ids = []
    for r in results:
        if r.case not in case_ids:
            case_ids.append(r.case)
    for case_id in case_ids:
        lines += [f"### {case_id}", "", "| Target | OK | Checks passed | 1st token | Total | Words | Notes |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for target in targets:
            for r in [x for x in results if x.case == case_id and x.target == target]:
                passed = sum(c["passed"] for c in r.checks)
                failed = [c["name"] for c in r.checks if not c["passed"]]
                notes = ("failed: " + "; ".join(failed)) if failed else (r.error or "")
                lines.append(
                    f"| `{target}` | {'yes' if r.ok else 'NO'} | {passed}/{len(r.checks)} | "
                    f"{r.ttft if r.ttft is not None else '-'}s | {r.total if r.total is not None else '-'}s | "
                    f"{r.style.get('words', '-')} | {notes} |"
                )
        lines.append("")
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    all_cases = build_cases()
    if args.list:
        for c in all_cases:
            print(f"{c.id:20} {c.title}")
        return 0
    cases = [c for c in all_cases if not args.only or c.id in args.only.split(",")]
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]

    results: List[Result] = []
    cold: Dict[str, Optional[float]] = {}
    for target in targets:
        provider_name, _, model = target.partition(":")
        provider = get_provider(provider_name)
        if not provider.is_configured():
            print(f"skipping {target}: provider not configured")
            continue
        if provider.kind == "local":
            unload_ollama_models(settings.ollama_base_url, except_model=model)
            if args.cold:
                unload_ollama_models(settings.ollama_base_url)
        print(f"\n== {target}")
        cold[target] = await warm_up(provider_name, model)
        print(f"   warm-up/cold-start: {cold[target]}s")
        for case in cases:
            for run in range(args.runs):
                result = await run_case(provider_name, model, case)
                results.append(result)
                passed = sum(c["passed"] for c in result.checks)
                print(f"   {case.id:20} ok={result.ok!s:5} checks={passed}/{len(result.checks)} ttft={result.ttft} total={result.total}s {result.error}")

    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_targets = [t for t in targets if any(r.target == t for r in results)]
    summary = summarize(results, run_targets, cold)
    with open(os.path.join(args.out, f"benchmark-{stamp}.json"), "w", encoding="utf-8") as handle:
        json.dump([r.__dict__ for r in results], handle, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, f"benchmark-{stamp}.md"), "w", encoding="utf-8") as handle:
        handle.write(summary)
    print("\n" + summary)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Rinti-AI models.")
    parser.add_argument("--targets", default=f"ollama:{settings.default_model}", help="comma list of provider:model")
    parser.add_argument("--only", default="", help="comma list of case ids")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--cold", action="store_true", help="unload all local models first")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "benchmarks"))
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
