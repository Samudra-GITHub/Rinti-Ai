"""Local extraction fallback: guarded fetch -> trafilatura -> BeautifulSoup.

This path also supplies publication dates, which the Tavily API does not return.
Every fetch goes through the SSRF validator, including each redirect hop.
"""

import asyncio
from typing import Optional, Tuple

import httpx2

from research.providers.base import RawExtraction
from research.security import (
    FETCH_TIMEOUT_SECONDS,
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    UnsafeUrlError,
    validate_url,
)

USER_AGENT = "RintiResearch/1.0 (+https://github.com/) python-httpx"

ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml", "text/plain", "application/xml", "text/xml")


async def _fetch(url: str) -> Tuple[str, str]:
    """Fetch a URL with redirects validated per hop. Returns (final_url, body_text)."""
    current = validate_url(url).url

    async with httpx2.AsyncClient(
        timeout=httpx2.Timeout(FETCH_TIMEOUT_SECONDS),
        follow_redirects=False,  # we follow manually so every hop is re-validated
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain"},
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            response = await client.get(current)

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise UnsafeUrlError("redirect without location header")
                nxt = str(httpx2.URL(current).join(location))
                current = validate_url(nxt).url  # re-validate every hop
                continue

            if response.status_code != 200:
                raise UnsafeUrlError(f"http status {response.status_code}")

            content_type = (response.headers.get("content-type") or "").lower()
            if content_type and not any(ct in content_type for ct in ALLOWED_CONTENT_TYPES):
                raise UnsafeUrlError(f"unsupported content type '{content_type.split(';')[0]}'")

            body = response.content[:MAX_RESPONSE_BYTES]
            return current, body.decode(response.encoding or "utf-8", errors="replace")

    raise UnsafeUrlError("too many redirects")


def _parse(html: str, url: str) -> Tuple[str, Optional[str], Optional[str], str]:
    """Return (text, title, publication_date, method)."""
    # 1. trafilatura — best quality, and gives us metadata incl. date
    try:
        import trafilatura

        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        if text and text.strip():
            title = None
            date = None
            try:
                meta = trafilatura.extract_metadata(html)
                if meta is not None:
                    title = getattr(meta, "title", None)
                    date = getattr(meta, "date", None)
            except Exception:
                pass
            return text.strip(), title, date, "trafilatura"
    except Exception:
        pass

    # 2. BeautifulSoup fallback
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else None

        date = None
        for selector, attr in (
            ({"property": "article:published_time"}, "content"),
            ({"name": "pubdate"}, "content"),
            ({"itemprop": "datePublished"}, "content"),
        ):
            tag = soup.find("meta", attrs=selector)
            if tag and tag.get(attr):
                date = tag.get(attr)
                break

        text = " ".join(soup.get_text(separator=" ", strip=True).split())
        return text, title, date, "beautifulsoup"
    except Exception:
        return "", None, None, "none"


async def extract_local(url: str) -> RawExtraction:
    """Fetch and extract a single URL locally. Never raises — failures are reported."""
    try:
        final_url, html = await _fetch(url)
    except UnsafeUrlError as exc:
        return RawExtraction(url=url, method="local", failed=True, error=str(exc))
    except Exception as exc:
        return RawExtraction(url=url, method="local", failed=True, error=f"fetch failed ({type(exc).__name__})")

    text, title, date, method = _parse(html, final_url)
    if not text:
        return RawExtraction(url=final_url, method=method, failed=True, error="no extractable text")

    return RawExtraction(
        url=final_url,
        content=text,
        title=(title or "").strip(),
        published_date=date,
        method=method,
    )


async def extract_many_local(urls, concurrency: int = 3):
    semaphore = asyncio.Semaphore(concurrency)

    async def run(u):
        async with semaphore:
            return await extract_local(u)

    return await asyncio.gather(*(run(u) for u in urls), return_exceptions=False)
