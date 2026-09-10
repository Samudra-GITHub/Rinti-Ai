"""Research-engine configuration.

Budgets live here rather than being hardcoded through the engine so they can be
tuned without touching orchestration logic.
"""

import os
from dataclasses import dataclass

from research.models import ResearchMode


@dataclass(frozen=True)
class Budget:
    max_searches: int
    max_sources: int
    max_extractions: int
    max_subqueries: int


BUDGETS = {
    ResearchMode.QUICK: Budget(max_searches=2, max_sources=6, max_extractions=4, max_subqueries=2),
    ResearchMode.STANDARD: Budget(max_searches=5, max_sources=16, max_extractions=8, max_subqueries=5),
}

# Conservative starting point per R1.5 §8 — raise only after measuring real behaviour.
MAX_CONCURRENT_SEARCHES = 3
MAX_CONCURRENT_EXTRACTIONS = 3

# Cache TTLs (seconds). Fresh/news-ish queries get a much shorter life.
SEARCH_CACHE_TTL = 900          # 15 min
EXTRACT_CACHE_TTL = 86_400      # 24 h
FRESH_SEARCH_CACHE_TTL = 180    # 3 min

# Cap how much extracted text per source reaches the model.
# MAX_TOTAL_EVIDENCE_CHARS is sized against the live Groq account's real rate
# limit (measured: on-demand tier caps at 8000 TPM), not just a guess — the
# original 40_000 char budget alone worked out to ~10k evidence tokens, which
# together with the ~1.2k-token system prompt and the 1400-token completion
# reservation routinely tripped a 413 "tokens per minute" rejection.
MAX_CONTENT_CHARS_PER_SOURCE = 3_500
MAX_TOTAL_EVIDENCE_CHARS = 12_000

# R1.6B: synthesis now asks for a structured JSON object instead of prose,
# which costs more completion tokens per unit of content (JSON punctuation/
# keys overhead) — evidence budget above was trimmed further to leave room
# for it within the same measured 8000 TPM account ceiling.
MAX_SYNTHESIS_TOKENS = 2200


def tavily_api_key() -> str:
    return (os.getenv("TAVILY_API_KEY") or "").strip()


def research_available() -> bool:
    """Whether real web research can run at all right now."""
    return bool(tavily_api_key())


RESEARCH_UNAVAILABLE_MESSAGE = (
    "Web research isn't available right now — no search provider is configured on the "
    "server. I'd rather tell you that than hand you an answer I couldn't actually verify."
)
