"""Source normalization, deduplication and quality scoring.

Deliberately deterministic — no model call decides how trustworthy a source is.
Lower-tier sources are kept (they carry real user sentiment) but they are scored
so they cannot silently outweigh primary evidence.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse, urlunparse

from research.models import ResearchSource, SourceTier
from research.providers.base import RawSearchResult

# Tracking params that create false "distinct" URLs.
_TRACKING_PARAMS = re.compile(
    r"^(utm_[a-z]+|fbclid|gclid|mc_[a-z]+|ref|ref_src|source|igshid|si|spm|_hsenc|_hsmi)$", re.I
)

_OFFICIAL_TLDS = (".gov", ".gov.in", ".gov.uk", ".mil", ".edu", ".ac.uk", ".ac.in", ".int")
_OFFICIAL_DOMAINS = {
    "who.int", "europa.eu", "iso.org", "ietf.org", "rfc-editor.org", "w3.org", "nist.gov",
    "arxiv.org", "doi.org", "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "sec.gov",
    "developer.mozilla.org", "docs.python.org", "nodejs.org", "nextjs.org", "react.dev",
    "kernel.org", "postgresql.org", "sqlite.org", "python.org", "golang.org", "rust-lang.org",
    "openai.com", "anthropic.com", "google.com", "apple.com", "microsoft.com", "nvidia.com",
    "semanticscholar.org", "openalex.org", "crossref.org", "nature.com", "science.org",
}
_ESTABLISHED_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com", "wsj.com",
    "bloomberg.com", "ft.com", "theguardian.com", "economist.com", "npr.org",
    "arstechnica.com", "theverge.com", "techcrunch.com", "wired.com", "anandtech.com",
    "tomshardware.com", "rtings.com", "dpreview.com", "notebookcheck.net", "gsmarena.com",
    "thehindu.com", "indianexpress.com", "livemint.com", "business-standard.com",
    "wikipedia.org", "stackoverflow.com", "github.com",
}
_COMMUNITY_DOMAINS = {
    "reddit.com", "news.ycombinator.com", "quora.com", "medium.com", "dev.to",
    "substack.com", "blogspot.com", "wordpress.com", "x.com", "twitter.com",
    "facebook.com", "linkedin.com", "youtube.com", "discord.com",
}
_LOW_TRUST_MARKERS = ("blogspot.", ".xyz", ".top", ".click", "content-farm", "seo-", "aggregator")


def canonicalize_url(raw_url: str) -> str:
    """Strip tracking params, fragments, default ports and trailing slashes."""
    try:
        parsed = urlparse(raw_url.strip())
    except Exception:
        return raw_url.strip()

    netloc = (parsed.hostname or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if parsed.port and not ((parsed.scheme == "http" and parsed.port == 80) or (parsed.scheme == "https" and parsed.port == 443)):
        netloc = f"{netloc}:{parsed.port}"

    kept = []
    for pair in (parsed.query or "").split("&"):
        if not pair:
            continue
        key = pair.split("=", 1)[0]
        if not _TRACKING_PARAMS.match(key):
            kept.append(pair)

    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    return urlunparse(("https", netloc, path, "", "&".join(sorted(kept)), ""))


def domain_of(raw_url: str) -> str:
    host = (urlparse(raw_url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _registrable(domain: str) -> str:
    """Cheap eTLD+1 approximation, good enough for grouping syndicated copies."""
    parts = domain.split(".")
    if len(parts) <= 2:
        return domain
    if parts[-2] in {"co", "com", "ac", "gov", "org", "net"} and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def classify_tier(domain: str) -> SourceTier:
    d = domain.lower()
    reg = _registrable(d)

    if d in _OFFICIAL_DOMAINS or reg in _OFFICIAL_DOMAINS or d.endswith(_OFFICIAL_TLDS):
        return SourceTier.OFFICIAL
    if d in _ESTABLISHED_DOMAINS or reg in _ESTABLISHED_DOMAINS:
        return SourceTier.ESTABLISHED
    if d in _COMMUNITY_DOMAINS or reg in _COMMUNITY_DOMAINS:
        return SourceTier.COMMUNITY
    if any(marker in d for marker in _LOW_TRUST_MARKERS):
        return SourceTier.LOW_TRUST
    # Unknown domains sit at community level — not trusted, not discarded.
    return SourceTier.COMMUNITY


_AUTHORITY_BY_TIER = {
    SourceTier.OFFICIAL: 1.0,
    SourceTier.ESTABLISHED: 0.75,
    SourceTier.COMMUNITY: 0.45,
    SourceTier.LOW_TRUST: 0.15,
}


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(text[: len(fmt) + 8], fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def freshness_score(publication_date: Optional[str]) -> float:
    """1.0 = today, decaying to 0.0 at ~3 years. Unknown dates get a neutral 0.5."""
    parsed = _parse_date(publication_date)
    if parsed is None:
        return 0.5
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - parsed).days
    if age_days < 0:
        return 1.0
    if age_days <= 7:
        return 1.0
    if age_days >= 1095:
        return 0.0
    return max(0.0, 1.0 - (age_days / 1095.0))


def _source_id(canonical: str) -> str:
    return "src_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def normalize_results(
    results: Iterable[RawSearchResult],
    *,
    provider: str = "tavily",
) -> List[ResearchSource]:
    """Turn provider hits into normalized sources, deduplicated and scored."""
    by_canonical: Dict[str, ResearchSource] = {}
    seen_title_domain: Dict[str, str] = {}

    for result in results:
        if not result.url:
            continue
        canonical = canonicalize_url(result.url)
        domain = domain_of(canonical) or domain_of(result.url)
        if not domain:
            continue

        # Dedup 1: identical canonical URL
        if canonical in by_canonical:
            existing = by_canonical[canonical]
            existing.relevance_score = max(existing.relevance_score, float(result.score or 0.0))
            if not existing.snippet and result.snippet:
                existing.snippet = result.snippet
            continue

        # Dedup 2: same title on the same registrable domain (syndicated/duplicated copies)
        title_key = _title_key(result.title)
        if title_key:
            composite = f"{_registrable(domain)}::{title_key}"
            if composite in seen_title_domain:
                continue
            seen_title_domain[composite] = canonical

        tier = classify_tier(domain)
        source = ResearchSource(
            id=_source_id(canonical),
            url=result.url,
            canonical_url=canonical,
            title=(result.title or domain).strip(),
            domain=domain,
            publisher=domain,
            publication_date=result.published_date,
            search_provider=provider,
            relevance_score=float(result.score or 0.0),
            authority_score=_AUTHORITY_BY_TIER[tier],
            freshness_score=freshness_score(result.published_date),
            tier=tier,
            snippet=(result.snippet or "").strip(),
            content=(result.raw_content or "").strip(),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )
        by_canonical[canonical] = source

    return list(by_canonical.values())


def rank_sources(sources: List[ResearchSource], *, prefer_fresh: bool) -> List[ResearchSource]:
    """Deterministic ordering: relevance + authority, with freshness weighted up for current queries."""
    fresh_weight = 0.35 if prefer_fresh else 0.1

    def score(s: ResearchSource) -> float:
        return (
            0.45 * min(max(s.relevance_score, 0.0), 1.0)
            + 0.40 * s.authority_score
            + fresh_weight * s.freshness_score
        )

    return sorted(sources, key=score, reverse=True)


def independence_ratio(sources: List[ResearchSource]) -> float:
    """Share of distinct registrable domains — low values mean weak corroboration."""
    if not sources:
        return 0.0
    domains = {_registrable(s.domain) for s in sources}
    return len(domains) / len(sources)
