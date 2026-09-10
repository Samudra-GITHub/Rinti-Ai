"""Structured research answer synthesis (R1.6B).

Core principle: the LLM writes content, the application controls structure.
The model is instructed to return a single JSON object matching a fixed
section-type vocabulary; this module parses and validates that JSON into
typed ResearchAnswer/AnswerSection objects and never lets an unrecognized
section type, or malformed JSON, reach the frontend as anything but a safe
plain-text fallback.

Citation *validation* (claims.py: evidence_supports_claim, validate_citations,
strip_invalid_citation_markers) is unchanged — this module only changes the
shape synthesis output takes before that validation runs, and extends
citation *extraction* to walk every text-bearing field of the structured tree
instead of one flat string.
"""

import json
import re
from typing import Any, Dict, List, Tuple

from research.claims import cited_statements
from research.models import (
    AnswerSection,
    Confidence,
    FactStatus,
    ResearchAnswer,
    ResearchEvidence,
    ResearchSource,
    SectionType,
)
from research.security import UNTRUSTED_CONTENT_NOTICE, wrap_untrusted

_ALLOWED_STATUSES = {s.value for s in FactStatus}

SYNTHESIS_INSTRUCTIONS = """You are producing a STRUCTURED research answer as a single JSON object.
Output ONLY the JSON object — no markdown code fences, no commentary before or after it.

{untrusted_notice}

Return exactly this JSON shape (top-level keys required; omit section fields you don't use):

{{
  "title": "short descriptive title for this research",
  "overview": "one concise paragraph summarizing the answer",
  "executive_summary": ["3 to 7 short key-finding strings"],
  "sections": [
    {{"type": "key_findings", "title": "Key Findings", "items": ["finding one", "finding two"]}},
    {{"type": "table", "title": "...", "columns": ["Model", "Price"], "rows": [["EOS R5", "$3899"]]}},
    {{"type": "comparison", "title": "...", "items": [{{"name": "...", "best_for": "...", "notes": "..."}}]}},
    {{"type": "timeline", "title": "...", "items": [{{"date": "...", "event": "..."}}]}},
    {{"type": "facts", "title": "Confirmed / Official", "status": "CONFIRMED", "items": ["..."]}},
    {{"type": "facts", "title": "Rumored / Unconfirmed", "status": "RUMORED", "items": ["..."]}},
    {{"type": "conflict", "title": "Conflicting Information", "content": "..."}},
    {{"type": "limitations", "title": "Limitations", "content": "..."}},
    {{"type": "analysis", "title": "...", "content": "..."}}
  ]
}}

Allowed section "type" values ONLY: overview, summary, key_findings, table, comparison,
timeline, pros_cons, facts, analysis, conflict, limitations. Never invent a new type — if
nothing fits, use "analysis" with a "content" paragraph.

Allowed section "status" values ONLY (use on "facts" sections, and on "conflict" when relevant):
OFFICIAL, CONFIRMED, REPORTED, RUMORED, SPECULATIVE.

Rules you must follow:
- Ground every factual claim in the numbered sources. Cite inline using PLAIN ASCII square
  brackets exactly like [1] or [2], attached directly to the sentence, list item, or table
  cell it supports. Do not use 【】, ［］ or any other bracket form. ONLY use
  citation numbers that appear in the evidence list below. Never invent a number.
- Separate confirmed/official information from rumors, leaks, or speculation into different
  "facts" sections with the correct "status" — never blend them into one list or table
  without a status field distinguishing them.
- Only produce a "table" section when the evidence actually supports a structured comparison
  (specs, prices, dates, etc). Keep tables to 5 columns or fewer — split a wide comparison into
  multiple smaller tables instead of one wide one.
- Choose only the sections that actually fit this question. A simple factual question may need
  only "overview" plus one or two more sections — do not force irrelevant sections in.
- If sources disagree, use a "conflict" section: explain what each side says, why the
  disagreement may exist, and what remains uncertain. Do not silently pick one value.
- If the evidence does not cover something, say so in a "limitations" section rather than
  filling the gap from memory. Never present unverified detail as fact.
- Do not create a "sources" section or list URLs/source metadata anywhere in the JSON — the
  interface renders sources separately from structured source objects it already has.
- Write as Rinti: warm, calm, clear, professional — never sterile, never a dry report dump.

Question: {question}

Evidence:
{evidence}"""


def build_evidence_blocks(
    sources: List[ResearchSource],
    evidence: List[ResearchEvidence],
    numbering: Dict[str, int],
) -> str:
    blocks = []
    evidence_by_source = {e.source_id: e for e in evidence}
    for source in sources:
        ev = evidence_by_source.get(source.id)
        if ev is None:
            continue
        n = numbering[source.id]
        label = f"[{n}] {source.title} — {source.domain}"
        if source.publication_date:
            label += f" ({source.publication_date})"
        blocks.append(f"{label}\n{wrap_untrusted(ev.snippet, source_label=source.domain)}")
    return "\n\n".join(blocks) if blocks else "(no evidence collected)"


def build_synthesis_prompt(question: str, evidence_text: str) -> str:
    return SYNTHESIS_INSTRUCTIONS.format(
        untrusted_notice=UNTRUSTED_CONTENT_NOTICE,
        question=question,
        evidence=evidence_text,
    )


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_code_fence(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text.strip()).strip()


def _coerce_status(value: Any) -> "FactStatus | None":
    if not value:
        return None
    text = str(value).strip().upper()
    return FactStatus(text) if text in _ALLOWED_STATUSES else None


def _coerce_str_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_str_matrix(value: Any) -> List[List[str]]:
    if not isinstance(value, list):
        return []
    rows: List[List[str]] = []
    for row in value:
        if isinstance(row, list):
            rows.append([str(cell) for cell in row])
    return rows


def parse_structured_answer(raw_text: str, query: str) -> Tuple[ResearchAnswer, List[str]]:
    """Parses the model's JSON into a ResearchAnswer. Never raises — malformed
    or partial output degrades to a minimal answer with a note explaining why,
    rather than crashing the research turn."""
    notes: List[str] = []
    cleaned = _strip_code_fence(raw_text)

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("top-level JSON value was not an object")
    except (json.JSONDecodeError, ValueError):
        # Degrade gracefully: treat the raw text as a single text section so the
        # user still gets an answer instead of an error, and we're honest that
        # structure parsing failed.
        notes.append("structured answer could not be parsed; showing raw text")
        fallback = ResearchAnswer(
            title=query[:120],
            query=query,
            overview="",
            executive_summary=[],
            sections=[AnswerSection(type=SectionType.TEXT, title="", content=raw_text.strip())],
        )
        return fallback, notes

    sections: List[AnswerSection] = []
    for raw_section in data.get("sections") or []:
        if not isinstance(raw_section, dict):
            continue
        section_type = SectionType.coerce(raw_section.get("type", "text"))
        if section_type.value not in {t.value for t in SectionType}:
            section_type = SectionType.TEXT
        sections.append(
            AnswerSection(
                type=section_type,
                title=str(raw_section.get("title") or ""),
                content=str(raw_section.get("content") or ""),
                items=_coerce_str_list(raw_section.get("items")),
                columns=[str(c) for c in raw_section.get("columns")] if isinstance(raw_section.get("columns"), list) else [],
                rows=_coerce_str_matrix(raw_section.get("rows")),
                status=_coerce_status(raw_section.get("status")),
            )
        )

    answer = ResearchAnswer(
        title=str(data.get("title") or query[:120]),
        query=query,
        overview=str(data.get("overview") or ""),
        executive_summary=_coerce_str_list(data.get("executive_summary")),
        sections=sections,
    )
    return answer, notes


def _section_text_fragments(section: AnswerSection) -> List[str]:
    """Every citable prose fragment inside one section, as flat strings —
    table rows and dict-shaped items are joined into one line per row/item so
    cited_statements() can find citation markers wherever they landed."""
    fragments: List[str] = []
    if section.content:
        fragments.append(section.content)
    for item in section.items:
        if isinstance(item, dict):
            fragments.append(" ".join(str(v) for v in item.values() if v))
        else:
            fragments.append(str(item))
    for row in section.rows:
        fragments.append(" ".join(row))
    return fragments


def citable_fragments(answer: ResearchAnswer) -> List[Tuple[int, str]]:
    """(citation_number, statement) pairs across the entire structured answer —
    the structured-tree equivalent of claims.cited_statements() on one string."""
    pairs: List[Tuple[int, str]] = []
    if answer.overview:
        pairs.extend(cited_statements(answer.overview))
    for finding in answer.executive_summary:
        pairs.extend(cited_statements(str(finding)))
    for section in answer.sections:
        for fragment in _section_text_fragments(section):
            pairs.extend(cited_statements(fragment))
    return pairs


def strip_invalid_markers_from_answer(answer: ResearchAnswer, valid_numbers: set) -> List[int]:
    """Mutates answer in place, removing any [n] marker that doesn't map to a
    real source — mirrors claims.strip_invalid_citation_markers but applied
    across every text field instead of one string. Returns removed numbers."""
    from research.claims import strip_invalid_citation_markers

    removed_all: List[int] = []

    def clean(text: str) -> str:
        cleaned, removed = strip_invalid_citation_markers(text, valid_numbers)
        removed_all.extend(removed)
        return cleaned

    answer.overview = clean(answer.overview)
    answer.executive_summary = [clean(str(f)) for f in answer.executive_summary]
    for section in answer.sections:
        section.content = clean(section.content)
        cleaned_items = []
        for item in section.items:
            if isinstance(item, dict):
                cleaned_items.append({k: (clean(str(v)) if isinstance(v, str) else v) for k, v in item.items()})
            else:
                cleaned_items.append(clean(str(item)))
        section.items = cleaned_items
        section.rows = [[clean(cell) for cell in row] for row in section.rows]

    return removed_all


def flatten_to_text(answer: ResearchAnswer) -> str:
    """Plain markdown-ish text for conversation history / LLM follow-up
    context and non-JS fallback — not what the frontend renders, but what
    a later turn's model call sees as 'what was said'."""
    lines: List[str] = []
    if answer.title:
        lines.append(f"# {answer.title}")
    if answer.overview:
        lines.append(answer.overview)
    if answer.executive_summary:
        lines.append("## Key Findings")
        lines.extend(f"- {f}" for f in answer.executive_summary)

    for section in answer.sections:
        if section.title:
            lines.append(f"## {section.title}")
        if section.content:
            lines.append(section.content)
        if section.columns and section.rows:
            lines.append(" | ".join(section.columns))
            for row in section.rows:
                lines.append(" | ".join(row))
        for item in section.items:
            if isinstance(item, dict):
                lines.append("- " + ", ".join(f"{k}: {v}" for k, v in item.items() if v))
            else:
                lines.append(f"- {item}")
    return "\n\n".join(lines).strip()
