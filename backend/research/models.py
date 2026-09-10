"""Normalized internal representations for the research engine.

Everything downstream of the search providers speaks these types — no vendor
payload shape is allowed to leak past the provider layer.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class ResearchIntent(str, Enum):
    NO_RESEARCH = "NO_RESEARCH"
    CURRENT_INFORMATION = "CURRENT_INFORMATION"
    FACT_CHECK = "FACT_CHECK"
    COMPARISON = "COMPARISON"
    PRODUCT_RESEARCH = "PRODUCT_RESEARCH"
    NEWS_RESEARCH = "NEWS_RESEARCH"
    GENERAL_RESEARCH = "GENERAL_RESEARCH"

    @property
    def needs_research(self) -> bool:
        return self is not ResearchIntent.NO_RESEARCH


class ResearchMode(str, Enum):
    QUICK = "QUICK"
    STANDARD = "STANDARD"


class SourceTier(int, Enum):
    """Lower number = more authoritative. Used for weighting, never for silent exclusion."""
    OFFICIAL = 1      # gov, standards bodies, official docs/specs, filings, papers
    ESTABLISHED = 2   # major publications, known technical press, methodical reviews
    COMMUNITY = 3     # forums, reddit, user reports, general blogs
    LOW_TRUST = 4     # SEO spam, scraped/unattributed content


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Stance(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class SourceType(str, Enum):
    """Content classification for display only — derived deterministically
    from the existing SourceTier, never from model judgment (R1.6B §16)."""
    OFFICIAL = "OFFICIAL"
    INDUSTRY = "INDUSTRY"
    ACADEMIC = "ACADEMIC"
    NEWS = "NEWS"
    USER_REPORTED = "USER_REPORTED"
    RUMOR = "RUMOR"
    OTHER = "OTHER"


class FactStatus(str, Enum):
    """How firmly a specific claim/section is established. Chosen by the model
    for the content it writes, but constrained to this fixed enum — the app
    controls what values exist, the model only picks among them (R1.6B core
    principle: LLM writes content, application controls structure)."""
    OFFICIAL = "OFFICIAL"
    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    RUMORED = "RUMORED"
    SPECULATIVE = "SPECULATIVE"


class SectionType(str, Enum):
    OVERVIEW = "overview"
    SUMMARY = "summary"
    KEY_FINDINGS = "key_findings"
    TABLE = "table"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    PROS_CONS = "pros_cons"
    FACTS = "facts"
    ANALYSIS = "analysis"
    CONFLICT = "conflict"
    LIMITATIONS = "limitations"
    SOURCES = "sources"
    # Fallback for anything the model emits that isn't a known type above —
    # never rendered as anything but plain text (R1.6B §2).
    TEXT = "text"

    @classmethod
    def coerce(cls, value: str) -> "SectionType":
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return cls.TEXT


@dataclass
class ResearchSource:
    id: str
    url: str
    canonical_url: str
    title: str
    domain: str
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    source_type: str = "web"
    search_provider: str = "tavily"
    relevance_score: float = 0.0
    authority_score: float = 0.0
    freshness_score: float = 0.0
    tier: SourceTier = SourceTier.COMMUNITY
    snippet: str = ""
    content: str = ""
    extraction_method: Optional[str] = None
    retrieved_at: Optional[str] = None

    # Deterministic tier -> display type/status mapping. Never LLM-decided —
    # source *evaluation* (tier/authority/freshness) is untouched R1.5 logic;
    # this only translates it into the vocabulary the R1.6B UI expects.
    _TYPE_BY_TIER = {
        SourceTier.OFFICIAL: SourceType.OFFICIAL,
        SourceTier.ESTABLISHED: SourceType.NEWS,
        SourceTier.COMMUNITY: SourceType.USER_REPORTED,
        SourceTier.LOW_TRUST: SourceType.OTHER,
    }
    _STATUS_BY_TIER = {
        SourceTier.OFFICIAL: "Official",
        SourceTier.ESTABLISHED: "Independent",
        SourceTier.COMMUNITY: "User-reported",
        SourceTier.LOW_TRUST: "Low-confidence",
    }

    def to_public(self, citation_number: int) -> Dict[str, Any]:
        """The only shape ever sent to the browser.

        Deliberately omits raw full content and internal scoring internals the UI
        has no use for; labels are pre-computed so the client does no judging.
        """
        labels: List[str] = [self._STATUS_BY_TIER.get(self.tier, "Low-confidence")]
        if self.freshness_score >= 0.7:
            labels.append("Recent")
        elif self.publication_date and self.freshness_score < 0.35:
            labels.append("Older")

        if self.authority_score >= 0.85:
            confidence = "HIGH"
        elif self.authority_score >= 0.5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return {
            "n": citation_number,
            "id": self.id,
            "url": self.url,
            "title": self.title or self.domain,
            "domain": self.domain,
            "publisher": self.publisher,
            "source_type": self._TYPE_BY_TIER.get(self.tier, SourceType.OTHER).value,
            "status": self._STATUS_BY_TIER.get(self.tier, "Low-confidence"),
            "confidence": confidence,
            "publication_date": self.publication_date,
            "retrieved_at": self.retrieved_at,
            "labels": labels,
            "excerpt": (self.snippet or self.content[:280]).strip(),
        }


@dataclass
class ResearchEvidence:
    id: str
    source_id: str
    snippet: str
    context: str = ""
    stance: Stance = Stance.NEUTRAL


@dataclass
class ResearchClaim:
    id: str
    text: str
    topic: str = ""
    claim_type: str = "factual"
    confidence_level: Confidence = Confidence.LOW
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)


@dataclass
class ResearchCitation:
    claim_id: str
    source_id: str
    evidence_id: str
    citation_number: int


@dataclass
class SubQuery:
    text: str
    purpose: str = ""


@dataclass
class ResearchPlan:
    intent: ResearchIntent
    primary_question: str
    subqueries: List[SubQuery] = field(default_factory=list)
    evidence_categories: List[str] = field(default_factory=list)
    requires_freshness: bool = False
    depth: ResearchMode = ResearchMode.QUICK


@dataclass
class ResearchBudgetUsage:
    search_calls: int = 0
    pages_extracted: int = 0
    failures: int = 0
    elapsed_seconds: float = 0.0
    cache_hits: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnswerSection:
    """One typed block of a structured research answer.

    Not every field applies to every type — a table uses columns/rows, a
    comparison/timeline/facts/pros_cons section uses items, overview/summary/
    analysis/conflict/limitations/text use content. Unused fields stay empty;
    the frontend renderer picks which fields it reads based on `type`.
    """
    type: SectionType
    title: str = ""
    content: str = ""
    items: List[Any] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    status: Optional[FactStatus] = None

    def to_public(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "items": self.items,
            "columns": self.columns,
            "rows": self.rows,
            "status": self.status.value if self.status else None,
        }


@dataclass
class ResearchAnswer:
    """The structured presentation layer (R1.6B). Sits alongside the existing
    flat `ResearchResult.answer` text (kept for conversation history/LLM
    context) rather than replacing it — this is additive."""
    title: str = ""
    query: str = ""
    overview: str = ""
    executive_summary: List[str] = field(default_factory=list)
    sections: List[AnswerSection] = field(default_factory=list)

    def to_public(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "query": self.query,
            "overview": self.overview,
            "executive_summary": self.executive_summary,
            "sections": [s.to_public() for s in self.sections],
        }


@dataclass
class ResearchResult:
    session_id: str
    query: str
    intent: ResearchIntent
    mode: ResearchMode
    sources: List[ResearchSource] = field(default_factory=list)
    claims: List[ResearchClaim] = field(default_factory=list)
    evidence: List[ResearchEvidence] = field(default_factory=list)
    citations: List[ResearchCitation] = field(default_factory=list)
    answer: str = ""
    structured_answer: Optional[ResearchAnswer] = None
    partial: bool = False
    notes: List[str] = field(default_factory=list)
    usage: ResearchBudgetUsage = field(default_factory=ResearchBudgetUsage)
