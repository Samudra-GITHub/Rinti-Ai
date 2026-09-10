"""Query decomposition.

Produces a validated ResearchPlan. Simple questions deliberately get zero
subqueries — decomposition is only worth its latency on genuinely multi-part
questions (R1.5 §7).
"""

import json
from datetime import datetime, timezone
from typing import List

from research.config import BUDGETS
from research.intent import IntentDecision
from research.models import ResearchMode, ResearchPlan, SubQuery

_PLANNER_PROMPT = """You plan web research. Break the question into focused search queries.

Reply with ONLY a JSON object:
{{"primary_question": "<restated question>",
  "subqueries": [{{"text": "<search query>", "purpose": "<what it establishes>"}}],
  "evidence_categories": ["<kind of evidence needed>"],
  "requires_freshness": <true|false>}}

Rules:
- At most {max_subqueries} subqueries. Use FEWER for simple questions; use 1 if the
  question is already a single searchable fact.
- Each subquery must be a good standalone web search string, not a sentence to a person.
- Subqueries must be independent of each other so they can run in parallel.
- Do not invent specifics (model numbers, prices, dates) that are not in the question.

Today's date is {today}.
Research intent: {intent}
Question: {query}"""


def _fallback_plan(query: str, decision: IntentDecision, mode: ResearchMode) -> ResearchPlan:
    return ResearchPlan(
        intent=decision.intent,
        primary_question=query.strip(),
        subqueries=[SubQuery(text=query.strip(), purpose="direct search")],
        evidence_categories=[],
        requires_freshness=decision.requires_freshness,
        depth=mode,
    )


def build_plan(query: str, decision: IntentDecision, mode: ResearchMode) -> ResearchPlan:
    """Ask the model for a decomposition; fall back to a single direct search."""
    budget = BUDGETS[mode]

    try:
        from config import settings
        from core.brain import client

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[{
                "role": "user",
                "content": _PLANNER_PROMPT.format(
                    max_subqueries=budget.max_subqueries,
                    today=today,
                    intent=decision.intent.value,
                    query=query[:2000],
                ),
            }],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception:
        return _fallback_plan(query, decision, mode)

    # --- validate before trusting any of it ---
    subqueries: List[SubQuery] = []
    for item in (payload.get("subqueries") or [])[: budget.max_subqueries]:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
        elif isinstance(item, str):
            text, purpose = item.strip(), ""
        else:
            continue
        if 3 <= len(text) <= 300:
            subqueries.append(SubQuery(text=text, purpose=purpose[:160]))

    if not subqueries:
        return _fallback_plan(query, decision, mode)

    categories = [
        str(c).strip()[:80]
        for c in (payload.get("evidence_categories") or [])
        if isinstance(c, (str, int, float)) and str(c).strip()
    ][:8]

    primary = str(payload.get("primary_question") or "").strip() or query.strip()

    return ResearchPlan(
        intent=decision.intent,
        primary_question=primary[:500],
        subqueries=subqueries,
        evidence_categories=categories,
        # The heuristic freshness signal wins if either says fresh — being wrong toward
        # "prefer recent sources" is much cheaper than serving a stale answer.
        requires_freshness=bool(payload.get("requires_freshness")) or decision.requires_freshness,
        depth=mode,
    )
