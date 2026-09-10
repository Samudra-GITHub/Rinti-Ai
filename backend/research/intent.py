"""Research intent detection.

Two stages, cheapest first:

1. Deterministic heuristics settle the obvious cases with no model call at all —
   this is what keeps "what is a stack?" fast (R1.5 §41).
2. Anything genuinely ambiguous goes to the existing model for structured
   classification, with the result validated before it is trusted.

Routing is deliberately conservative: when the model is unavailable or returns
junk, we fall back to the heuristic verdict rather than researching everything.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from research.models import ResearchIntent

# --- deterministic signals -------------------------------------------------

_TEMPORAL = re.compile(
    r"\b(latest|newest|current|currently|today|todays|tonight|yesterday|this (?:week|month|year)|"
    r"right now|as of|recent|recently|just (?:released|announced|launched)|up[- ]to[- ]date|"
    r"still|now|202[4-9]|203\d)\b",
    re.I,
)
_NEWS = re.compile(r"\b(news|headline|happened|breaking|announced|released|launch|update[sd]?)\b", re.I)
_EVIDENCE = re.compile(
    r"\b(source[sd]?|cite|citation|evidence|verify|verified|fact[- ]check|is it true|"
    r"proof|according to|reference[sd]?|back(?:ed)? up)\b",
    re.I,
)
_PRODUCT = re.compile(
    r"\b(price|pricing|cost[s]?|cheap(?:est)?|buy|purchase|worth (?:it|buying)|deal|discount|"
    r"available|availability|in stock|spec(?:s|ification)s?|review[s]?)\b",
    re.I,
)
_CURRENCY = re.compile(r"[₹$€£¥]\s?\d|\b\d+\s?(?:usd|inr|eur|gbp|rupees|dollars)\b", re.I)
_COMPARISON = re.compile(r"\b(vs\.?|versus|compare[d]?|comparison|better than|which (?:one|is better)|best)\b", re.I)
_WHO_IS_CURRENT = re.compile(r"\b(who is|who's)\b.*\b(ceo|president|prime minister|chairman|head of|leader)\b", re.I)

# Static/definitional phrasing that, absent any temporal marker, does not need the web.
_DEFINITIONAL = re.compile(
    r"^\s*(what (?:is|are|does)|explain|define|how (?:do(?:es)?|to)|why (?:is|do|does)|"
    r"tell me about|help me understand|write|implement|refactor|debug|fix)\b",
    re.I,
)
_CODE_TASK = re.compile(
    r"\b(function|code|snippet|regex|algorithm|stack trace|error message|compile|syntax|"
    r"typescript|python|javascript|sql|css|html)\b",
    re.I,
)


@dataclass
class IntentDecision:
    intent: ResearchIntent
    requires_freshness: bool
    reason: str
    method: str  # "heuristic" | "model" | "fallback"

    @property
    def needs_research(self) -> bool:
        return self.intent.needs_research


def _heuristic(query: str) -> Optional[IntentDecision]:
    """Return a decision only when the signal is strong enough to skip the model."""
    q = (query or "").strip()
    if not q:
        return IntentDecision(ResearchIntent.NO_RESEARCH, False, "empty query", "heuristic")

    temporal = bool(_TEMPORAL.search(q))
    evidence = bool(_EVIDENCE.search(q))
    product = bool(_PRODUCT.search(q)) or bool(_CURRENCY.search(q))
    news = bool(_NEWS.search(q))
    comparison = bool(_COMPARISON.search(q))
    who_current = bool(_WHO_IS_CURRENT.search(q))

    if who_current:
        return IntentDecision(ResearchIntent.CURRENT_INFORMATION, True, "asks who currently holds a role", "heuristic")
    if evidence:
        return IntentDecision(ResearchIntent.FACT_CHECK, temporal, "explicitly asks for sources/verification", "heuristic")
    if news and temporal:
        return IntentDecision(ResearchIntent.NEWS_RESEARCH, True, "asks about recent events", "heuristic")
    if product and (temporal or comparison or _CURRENCY.search(q)):
        return IntentDecision(ResearchIntent.PRODUCT_RESEARCH, True, "asks about current product pricing/availability", "heuristic")
    if temporal and not _CODE_TASK.search(q):
        return IntentDecision(ResearchIntent.CURRENT_INFORMATION, True, "asks for current/latest information", "heuristic")

    # Strong "static" signal: definitional phrasing, no temporal/evidence/product markers.
    if _DEFINITIONAL.match(q) and not (temporal or evidence or product or news):
        return IntentDecision(ResearchIntent.NO_RESEARCH, False, "definitional question with no time-sensitive signal", "heuristic")

    if _CODE_TASK.search(q) and not (temporal or evidence):
        return IntentDecision(ResearchIntent.NO_RESEARCH, False, "coding task with no time-sensitive signal", "heuristic")

    return None  # ambiguous -> ask the model


_CLASSIFIER_PROMPT = """You classify whether a user question needs live web research.

Reply with ONLY a JSON object:
{{"intent": "<INTENT>", "requires_freshness": <true|false>, "reason": "<short reason>"}}

Valid INTENT values:
- NO_RESEARCH: answerable from general knowledge; stable concepts, definitions, coding help, reasoning, writing
- CURRENT_INFORMATION: needs present-day facts (who currently holds a role, latest version, current status)
- FACT_CHECK: asks whether a specific claim is true or asks for evidence
- COMPARISON: compares options where current facts matter
- PRODUCT_RESEARCH: prices, availability, specs, buying decisions
- NEWS_RESEARCH: recent events
- GENERAL_RESEARCH: needs multiple external sources but fits none of the above

Be conservative: prefer NO_RESEARCH when general knowledge genuinely suffices.
Today's date is {today}.

Question: {query}"""


def _classify_with_model(query: str) -> Optional[IntentDecision]:
    try:
        from config import settings
        from core.brain import client

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[{"role": "user", "content": _CLASSIFIER_PROMPT.format(today=today, query=query[:2000])}],
            temperature=0,
            max_tokens=160,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        raw_intent = str(payload.get("intent", "")).strip().upper()
        if raw_intent not in ResearchIntent.__members__:
            return None
        return IntentDecision(
            intent=ResearchIntent[raw_intent],
            requires_freshness=bool(payload.get("requires_freshness", False)),
            reason=str(payload.get("reason", ""))[:200],
            method="model",
        )
    except Exception:
        return None


def detect_intent(query: str, *, allow_model: bool = True) -> IntentDecision:
    decision = _heuristic(query)
    if decision is not None:
        return decision

    if allow_model:
        model_decision = _classify_with_model(query)
        if model_decision is not None:
            return model_decision

    # Conservative fallback: without a confident signal, don't burn a research budget.
    return IntentDecision(
        ResearchIntent.NO_RESEARCH,
        False,
        "no clear research signal and classifier unavailable",
        "fallback",
    )
