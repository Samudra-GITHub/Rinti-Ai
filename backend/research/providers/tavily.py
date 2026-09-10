"""Tavily search provider.

Contract verified against https://docs.tavily.com (Sept 2026):
  - POST https://api.tavily.com/search
  - POST https://api.tavily.com/extract
  - Auth: `Authorization: Bearer tvly-...`
  - Neither endpoint returns a publication date, so freshness has to come from
    local extraction metadata or from search-level `time_range` biasing.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx2

from research.config import tavily_api_key
from research.providers.base import (
    RawExtraction,
    RawSearchResult,
    SearchProvider,
    SearchProviderError,
    SearchQuery,
)

SEARCH_URL = "https://api.tavily.com/search"
EXTRACT_URL = "https://api.tavily.com/extract"

REQUEST_TIMEOUT = 25.0
MAX_ATTEMPTS = 3


class TavilySearchProvider(SearchProvider):
    name = "tavily"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = (api_key or tavily_api_key()).strip()
        if not self._api_key:
            raise SearchProviderError("TAVILY_API_KEY is not configured")
        self._client = httpx2.AsyncClient(
            timeout=httpx2.Timeout(REQUEST_TIMEOUT),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    async def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        last_error: Optional[str] = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = await self._client.post(url, json=payload)
            except Exception as exc:  # network-level failure
                last_error = f"network error ({type(exc).__name__})"
                await asyncio.sleep(0.6 * (attempt + 1))
                continue

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as exc:
                    raise SearchProviderError(f"malformed provider response ({type(exc).__name__})")

            if response.status_code in (401, 403):
                # Never echo the body — it can contain the key fragment.
                raise SearchProviderError("search provider rejected the credentials")
            if response.status_code == 429:
                last_error = "rate limited"
                await asyncio.sleep(1.2 * (attempt + 1))
                continue
            if response.status_code >= 500:
                last_error = f"provider error {response.status_code}"
                await asyncio.sleep(0.8 * (attempt + 1))
                continue

            raise SearchProviderError(f"provider returned status {response.status_code}")

        raise SearchProviderError(last_error or "provider unavailable", retryable=True)

    async def search(self, query: SearchQuery) -> List[RawSearchResult]:
        payload: Dict[str, Any] = {
            "query": query.query,
            "search_depth": "basic",
            "topic": query.topic if query.topic in ("general", "news", "finance") else "general",
            "max_results": max(1, min(query.max_results, 20)),
            "include_answer": False,
            "include_raw_content": "text" if query.include_raw_content else False,
        }
        if query.require_fresh:
            payload["time_range"] = "month"
        if query.domains:
            payload["include_domains"] = query.domains[:300]

        data = await self._post(SEARCH_URL, payload)

        results: List[RawSearchResult] = []
        for item in data.get("results") or []:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            results.append(
                RawSearchResult(
                    url=url,
                    title=(item.get("title") or "").strip(),
                    snippet=(item.get("content") or "").strip(),
                    # Verified: Tavily does not return a publication date.
                    published_date=None,
                    score=float(item.get("score") or 0.0),
                    raw_content=(item.get("raw_content") or "") or "",
                )
            )
        return results

    async def extract(self, urls: List[str]) -> List[RawExtraction]:
        if not urls:
            return []

        payload = {
            "urls": urls[:20],
            "extract_depth": "basic",
            "format": "text",
        }
        data = await self._post(EXTRACT_URL, payload)

        extractions: List[RawExtraction] = []
        for item in data.get("results") or []:
            extractions.append(
                RawExtraction(
                    url=(item.get("url") or "").strip(),
                    content=(item.get("raw_content") or "").strip(),
                    method="tavily_extract",
                )
            )
        for item in data.get("failed_results") or []:
            extractions.append(
                RawExtraction(
                    url=(item.get("url") or "").strip(),
                    method="tavily_extract",
                    failed=True,
                    error=str(item.get("error") or "extraction failed")[:200],
                )
            )
        return extractions

    async def aclose(self) -> None:
        await self._client.aclose()
