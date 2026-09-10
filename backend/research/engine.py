"""Research orchestrator.

SEARCH -> RETRIEVE -> EXTRACT -> EVALUATE -> CROSS-CHECK -> SYNTHESIZE -> CITE

Emits SSE frames in the same format the chat path already uses, so the frontend
parser is shared. Only high-level status and safe source metadata ever leave this
module — no plans, no prompts, no chain-of-thought (R1.5 §24/§25).
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from research.claims import (
    assess_confidence,
    build_evidence,
    make_claim,
    validate_citations,
)
from research.config import (
    BUDGETS,
    MAX_CONCURRENT_EXTRACTIONS,
    MAX_CONCURRENT_SEARCHES,
    MAX_CONTENT_CHARS_PER_SOURCE,
    MAX_SYNTHESIS_TOKENS,
    MAX_TOTAL_EVIDENCE_CHARS,
    RESEARCH_UNAVAILABLE_MESSAGE,
    research_available,
)
from research.evaluator import normalize_results, rank_sources, independence_ratio
from research.extractors.http import extract_local
from research.intent import IntentDecision, detect_intent
from research.models import (
    ResearchAnswer,
    ResearchCitation,
    ResearchEvidence,
    ResearchMode,
    ResearchResult,
    ResearchSource,
    Stance,
)
from research.planner import build_plan
from research.providers.base import SearchProviderError, SearchQuery
from research.providers.tavily import TavilySearchProvider
from research.security import wrap_untrusted
from research.synthesis import (
    build_evidence_blocks,
    build_synthesis_prompt,
    citable_fragments,
    flatten_to_text,
    parse_structured_answer,
    strip_invalid_markers_from_answer,
)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ResearchEngine:
    def __init__(self, provider=None):
        self._provider = provider
        self._owns_provider = provider is None

    async def _get_provider(self):
        if self._provider is None:
            self._provider = TavilySearchProvider()
        return self._provider

    async def _aclose(self):
        if self._owns_provider and self._provider is not None:
            try:
                await self._provider.aclose()
            except Exception:
                pass
            self._provider = None

    # -- search ------------------------------------------------------------
    async def _search_all(self, plan, budget) -> Tuple[List[ResearchSource], int, int]:
        provider = await self._get_provider()
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)
        queries = plan.subqueries[: budget.max_searches]

        async def run(sub) -> List:
            async with semaphore:
                q = SearchQuery(
                    query=sub.text,
                    max_results=max(3, budget.max_sources // max(1, len(queries))),
                    require_fresh=plan.requires_freshness,
                    topic="news" if plan.intent.value == "NEWS_RESEARCH" else "general",
                    include_raw_content=True,
                )
                return await provider.search(q)

        settled = await asyncio.gather(*(run(s) for s in queries), return_exceptions=True)

        raw_results = []
        failures = 0
        for outcome in settled:
            if isinstance(outcome, Exception):
                failures += 1  # partial failure is survivable (R1.5 §8)
                continue
            raw_results.extend(outcome)

        sources = normalize_results(raw_results, provider=provider.name)
        return sources, len(queries), failures

    # -- extraction --------------------------------------------------------
    async def _extract(self, sources: List[ResearchSource], budget) -> int:
        """Fill in full text for the top sources. Tavily raw_content first, local fetch otherwise."""
        needing = [s for s in sources[: budget.max_extractions] if len(s.content) < 400]
        if not needing:
            return 0

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)

        async def run(source: ResearchSource):
            async with semaphore:
                return source, await extract_local(source.url)

        extracted = 0
        for outcome in await asyncio.gather(*(run(s) for s in needing), return_exceptions=True):
            if isinstance(outcome, Exception):
                continue
            source, extraction = outcome
            if extraction.failed or not extraction.content:
                continue
            source.content = extraction.content[:MAX_CONTENT_CHARS_PER_SOURCE]
            source.extraction_method = extraction.method
            if extraction.published_date and not source.publication_date:
                source.publication_date = extraction.published_date
                from research.evaluator import freshness_score
                source.freshness_score = freshness_score(extraction.published_date)
            if extraction.title and not source.title:
                source.title = extraction.title
            extracted += 1
        return extracted

    # -- evidence ----------------------------------------------------------
    def _build_evidence(self, sources: List[ResearchSource]) -> List[ResearchEvidence]:
        evidence: List[ResearchEvidence] = []
        total = 0
        for source in sources:
            body = (source.content or source.snippet or "").strip()
            if not body:
                continue
            snippet = body[:MAX_CONTENT_CHARS_PER_SOURCE]
            if total + len(snippet) > MAX_TOTAL_EVIDENCE_CHARS:
                snippet = snippet[: max(0, MAX_TOTAL_EVIDENCE_CHARS - total)]
                if not snippet:
                    break
            total += len(snippet)
            evidence.append(build_evidence(source, snippet, stance=Stance.NEUTRAL))
        return evidence

    # -- synthesis ---------------------------------------------------------
    async def _synthesize(
        self,
        question: str,
        sources: List[ResearchSource],
        evidence: List[ResearchEvidence],
        numbering: Dict[str, int],
    ) -> Tuple["ResearchAnswer", List[str]]:
        """One non-streaming call that returns a structured JSON answer.

        Streaming raw tokens made sense for prose; it doesn't for JSON the
        frontend must parse as a whole. Progressive reveal now happens at the
        section level instead (run() emits one answer_section frame per
        parsed section right after this returns) — see R1.6B §12.
        """
        from config import settings
        from core.brain import client
        from core.personality import RINTI_SYSTEM_PROMPT

        evidence_text = build_evidence_blocks(sources, evidence, numbering)
        user_content = build_synthesis_prompt(question, evidence_text)

        response = client.chat.completions.create(
            model=settings.model_name,
            # Canonical identity stays in the system slot; evidence is user-role data.
            messages=[
                {"role": "system", "content": RINTI_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=MAX_SYNTHESIS_TOKENS,
        )
        raw_text = response.choices[0].message.content or ""
        answer, parse_notes = parse_structured_answer(raw_text, question)
        return answer, parse_notes

    # -- orchestration -----------------------------------------------------
    async def run(
        self,
        query: str,
        *,
        mode: ResearchMode = ResearchMode.QUICK,
        decision: Optional[IntentDecision] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[Tuple[str, ResearchResult], None]:
        """Yield SSE frames. The final ResearchResult rides along for persistence."""
        started = time.monotonic()
        session_id = session_id or f"rs_{uuid.uuid4().hex[:12]}"
        decision = decision or detect_intent(query)
        budget = BUDGETS[mode]

        result = ResearchResult(
            session_id=session_id,
            query=query,
            intent=decision.intent,
            mode=mode,
        )

        # Availability only gates building our own provider; an injected provider
        # (tests, or a future alternative backend) supplies its own credentials.
        if self._provider is None and not research_available():
            result.notes.append("no search provider configured")
            yield _sse("error", {"code": "research_unavailable", "message": RESEARCH_UNAVAILABLE_MESSAGE}), result
            return

        try:
            yield _sse("research_status", {"stage": "planning", "progress": 0.05, "label": "Planning research..."}), result
            plan = await asyncio.to_thread(build_plan, query, decision, mode)

            yield _sse("research_status", {"stage": "searching", "progress": 0.2, "label": "Searching the web..."}), result
            sources, search_calls, failures = await self._search_all(plan, budget)
            result.usage.search_calls = search_calls
            result.usage.failures = failures

            if not sources:
                result.partial = True
                result.notes.append("no usable sources found")
                yield _sse("error", {
                    "code": "no_sources",
                    "message": "I searched but couldn't find usable sources for that, so I don't want to guess at an answer.",
                }), result
                return

            sources = rank_sources(sources, prefer_fresh=plan.requires_freshness)[: budget.max_sources]

            yield _sse("research_status", {"stage": "reading", "progress": 0.45, "label": "Reading sources..."}), result
            result.usage.pages_extracted = await self._extract(sources, budget)

            # Drop sources that yielded nothing usable at all.
            sources = [s for s in sources if (s.content or s.snippet).strip()]
            if not sources:
                result.partial = True
                yield _sse("error", {
                    "code": "no_content",
                    "message": "I found pages but couldn't read enough from them to answer safely.",
                }), result
                return

            numbering = {s.id: i + 1 for i, s in enumerate(sources)}
            result.sources = sources

            for source in sources:
                yield _sse("source", source.to_public(numbering[source.id])), result

            yield _sse("research_status", {"stage": "cross_checking", "progress": 0.65, "label": "Cross-checking evidence..."}), result
            evidence = self._build_evidence(sources)
            result.evidence = evidence

            if failures:
                result.partial = True
                result.notes.append(f"{failures} search(es) failed; answer is based on partial coverage")
            if independence_ratio(sources) < 0.5:
                result.notes.append("most sources share a domain, so corroboration is limited")

            yield _sse("research_status", {"stage": "writing", "progress": 0.8, "label": "Writing answer..."}), result

            structured_answer, parse_notes = await self._synthesize(
                plan.primary_question or query, sources, evidence, numbering
            )
            result.notes.extend(parse_notes)

            # --- citation validation: nothing invented survives ---
            # Same claims.py functions R1.5 always used; only the extraction walk
            # now covers every text field of the structured tree, not one string.
            valid_numbers = set(numbering.values())
            removed = strip_invalid_markers_from_answer(structured_answer, valid_numbers)
            if removed:
                result.notes.append(f"removed {len(removed)} citation marker(s) that did not match a real source")

            by_number = {n: sid for sid, n in numbering.items()}
            evidence_by_source = {e.source_id: e for e in evidence}
            claims = []
            citations = []
            seen_claims = set()
            for number, statement in citable_fragments(structured_answer):
                source_id = by_number.get(number)
                ev = evidence_by_source.get(source_id) if source_id else None
                if not source_id or ev is None:
                    continue
                claim = make_claim(statement[:500], topic=query[:80])
                if claim.id not in seen_claims:
                    seen_claims.add(claim.id)
                    claims.append(claim)
                if ev.id not in claim.supporting_evidence_ids:
                    claim.supporting_evidence_ids.append(ev.id)
                citations.append(
                    ResearchCitation(claim_id=claim.id, source_id=source_id, evidence_id=ev.id, citation_number=number)
                )

            kept, rejected = validate_citations(citations, claims, evidence, sources)
            if rejected:
                result.notes.append(
                    f"{len(rejected)} citation(s) could not be substantiated by the cited source and were dropped"
                )
            for claim in claims:
                claim.confidence_level = assess_confidence(
                    claim, {e.id: e for e in evidence}, {s.id: s for s in sources}
                )
            result.claims = claims
            result.citations = kept
            result.structured_answer = structured_answer
            result.answer = flatten_to_text(structured_answer)
            result.usage.elapsed_seconds = round(time.monotonic() - started, 2)

            # Progressive reveal at section granularity (R1.6B §12) — the frontend
            # renders each typed section as it arrives instead of waiting for the
            # whole answer, without ever streaming raw/partial JSON it would have
            # to parse mid-flight.
            yield _sse("answer_meta", {
                "title": structured_answer.title,
                "overview": structured_answer.overview,
                "executive_summary": structured_answer.executive_summary,
            }), result
            for section in structured_answer.sections:
                yield _sse("answer_section", section.to_public()), result

            yield _sse("done", {
                "sessionId": session_id,
                "partial": result.partial,
                "notes": result.notes,
                "usage": result.usage.as_dict(),
            }), result

        except SearchProviderError as exc:
            result.partial = True
            result.notes.append(str(exc))
            yield _sse("error", {
                "code": "provider_error",
                "message": "I couldn't complete the web search just now, so I don't want to present an unverified answer.",
            }), result
        except Exception as exc:  # never leak internals to the browser
            print(f"[research engine error] {type(exc).__name__}")
            result.partial = True
            yield _sse("error", {
                "code": "research_failed",
                "message": "Something went wrong while researching that. Please try again.",
            }), result
        finally:
            await self._aclose()
