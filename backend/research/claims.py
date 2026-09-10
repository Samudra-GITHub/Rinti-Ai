"""Claim / evidence / citation layer.

The rule this file exists to enforce: a citation may only survive if the source
exists in *this* session, the evidence exists, the evidence belongs to that
source, and the evidence actually mentions what the claim asserts. Anything that
fails those checks is dropped rather than shown to the user.
"""

import hashlib
import re
from typing import Dict, List, Optional, Sequence, Tuple

from research.models import (
    Confidence,
    ResearchCitation,
    ResearchClaim,
    ResearchEvidence,
    ResearchSource,
    Stance,
)

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "of", "in", "on", "at",
    "to", "for", "with", "and", "or", "but", "it", "its", "this", "that", "these", "those",
    "as", "by", "from", "has", "have", "had", "will", "would", "can", "could", "about",
}

_NUMBER = re.compile(r"\d[\d,.]*")


def _evidence_id(source_id: str, snippet: str) -> str:
    digest = hashlib.sha256(f"{source_id}::{snippet}".encode("utf-8")).hexdigest()[:12]
    return f"ev_{digest}"


def _claim_id(text: str) -> str:
    return "clm_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _numbers(text: str) -> set:
    return {n.replace(",", "").rstrip(".") for n in _NUMBER.findall(text or "")}


def build_evidence(source: ResearchSource, snippet: str, *, stance: Stance = Stance.NEUTRAL, context: str = "") -> ResearchEvidence:
    snippet = (snippet or "").strip()
    return ResearchEvidence(
        id=_evidence_id(source.id, snippet),
        source_id=source.id,
        snippet=snippet,
        context=context,
        stance=stance,
    )


def make_claim(text: str, *, topic: str = "", claim_type: str = "factual") -> ResearchClaim:
    text = (text or "").strip()
    return ResearchClaim(id=_claim_id(text), text=text, topic=topic, claim_type=claim_type)


def evidence_supports_claim(claim_text: str, evidence_snippet: str, *, threshold: float = 0.35) -> bool:
    """Lexical support check.

    Deliberately conservative and deterministic. If the claim states a number, that
    number must appear in the evidence — this is what stops "X costs 20,000" from
    being 'supported' by evidence that says 10,000.
    """
    claim_tokens = _tokens(claim_text)
    evidence_tokens = _tokens(evidence_snippet)
    if not claim_tokens or not evidence_tokens:
        return False

    claim_numbers = _numbers(claim_text)
    if claim_numbers:
        evidence_numbers = _numbers(evidence_snippet)
        if not claim_numbers & evidence_numbers:
            return False

    overlap = len(claim_tokens & evidence_tokens) / len(claim_tokens)
    return overlap >= threshold


def assess_confidence(
    claim: ResearchClaim,
    evidence_by_id: Dict[str, ResearchEvidence],
    sources_by_id: Dict[str, ResearchSource],
) -> Confidence:
    """HIGH needs corroboration from independent domains or a single official source."""
    supporting = [evidence_by_id[e] for e in claim.supporting_evidence_ids if e in evidence_by_id]
    contradicting = [evidence_by_id[e] for e in claim.contradicting_evidence_ids if e in evidence_by_id]
    if not supporting:
        return Confidence.LOW

    domains = {sources_by_id[e.source_id].domain for e in supporting if e.source_id in sources_by_id}
    tiers = [sources_by_id[e.source_id].tier for e in supporting if e.source_id in sources_by_id]
    best_tier = min((t.value for t in tiers), default=4)

    if contradicting:
        return Confidence.LOW if len(contradicting) >= len(supporting) else Confidence.MEDIUM
    if len(domains) >= 2 and best_tier <= 2:
        return Confidence.HIGH
    if best_tier == 1:
        return Confidence.HIGH
    if len(domains) >= 2:
        return Confidence.MEDIUM
    return Confidence.MEDIUM if best_tier <= 2 else Confidence.LOW


def validate_citations(
    citations: Sequence[ResearchCitation],
    claims: Sequence[ResearchClaim],
    evidence: Sequence[ResearchEvidence],
    sources: Sequence[ResearchSource],
) -> Tuple[List[ResearchCitation], List[str]]:
    """Drop any citation that cannot be fully substantiated. Returns (kept, rejection reasons)."""
    claims_by_id = {c.id: c for c in claims}
    evidence_by_id = {e.id: e for e in evidence}
    sources_by_id = {s.id: s for s in sources}

    kept: List[ResearchCitation] = []
    rejected: List[str] = []

    for citation in citations:
        if citation.source_id not in sources_by_id:
            rejected.append(f"citation references unknown source {citation.source_id}")
            continue
        if citation.evidence_id not in evidence_by_id:
            rejected.append(f"citation references unknown evidence {citation.evidence_id}")
            continue
        if citation.claim_id not in claims_by_id:
            rejected.append(f"citation references unknown claim {citation.claim_id}")
            continue

        ev = evidence_by_id[citation.evidence_id]
        if ev.source_id != citation.source_id:
            rejected.append(f"evidence {ev.id} does not belong to source {citation.source_id}")
            continue

        claim = claims_by_id[citation.claim_id]
        if not evidence_supports_claim(claim.text, ev.snippet):
            rejected.append(f"evidence does not support claim {claim.id}")
            continue

        kept.append(citation)

    return kept, rejected


# Models routinely emit full-width / CJK bracket forms (【2】, ［2］) instead of ASCII.
# Those must be normalized before validation, or citations silently escape every
# check: they'd never be verified, never be stripped when hallucinated, and never
# map to a source.
_BRACKET_TRANSLATION = str.maketrans({
    "【": "[", "】": "]",
    "［": "[", "］": "]",
    "〔": "[", "〕": "]",
    "⟦": "[", "⟧": "]",
})

_CITATION_RE = re.compile(r"\[(\d{1,2})\]")


def normalize_citation_markers(answer: str) -> str:
    """Convert alternate bracket forms to ASCII so citation checks actually apply."""
    return (answer or "").translate(_BRACKET_TRANSLATION)


def cited_statements(answer: str) -> List[Tuple[int, str]]:
    """Pair each citation number with the sentence/line that actually carries it.

    The claim being validated has to be the real statement the citation is attached
    to — validating a synthetic placeholder would make the support check theatre.
    """
    text = normalize_citation_markers(answer)
    pairs: List[Tuple[int, str]] = []

    # Split into lines first. A markdown table row is kept as one atomic unit —
    # further splitting it on sentence-ending punctuation would sever a cell's
    # citation marker from the descriptive cell earlier in the same row (a
    # comparison row's prose commonly ends in a period before the source cell),
    # dropping every citation in table-formatted answers.
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        chunks = [line] if line.startswith("|") else re.split(r"(?<=[.!?])\s+", line)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            numbers = {int(n) for n in _CITATION_RE.findall(chunk)}
            if not numbers:
                continue
            statement = _CITATION_RE.sub("", chunk)
            statement = re.sub(r"[|*`#>_-]+", " ", statement)  # strip markdown noise
            statement = re.sub(r"\s{2,}", " ", statement).strip(" .")
            if not statement:
                continue
            for number in sorted(numbers):
                pairs.append((number, statement))
    return pairs


def extract_cited_numbers(answer: str) -> List[int]:
    """Citation markers actually used in the model's answer, e.g. '[3]'."""
    return [int(n) for n in _CITATION_RE.findall(normalize_citation_markers(answer))]


def strip_invalid_citation_markers(answer: str, valid_numbers: set) -> Tuple[str, List[int]]:
    """Remove any [n] marker that doesn't map to a real source in this session."""
    removed: List[int] = []

    def replace(match: re.Match) -> str:
        number = int(match.group(1))
        if number in valid_numbers:
            return match.group(0)
        removed.append(number)
        return ""

    cleaned = _CITATION_RE.sub(replace, normalize_citation_markers(answer))
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip(), removed
