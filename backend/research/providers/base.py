"""Search-provider interface.

The engine only ever talks to this abstraction, so adding Exa later means adding
one implementation — not touching orchestration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


class SearchProviderError(RuntimeError):
    """Provider failed in a way the engine should handle gracefully."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class RawSearchResult:
    """Provider-agnostic search hit, before normalization/scoring."""
    url: str
    title: str = ""
    snippet: str = ""
    published_date: Optional[str] = None
    score: float = 0.0
    raw_content: str = ""


@dataclass
class RawExtraction:
    url: str
    content: str = ""
    title: str = ""
    published_date: Optional[str] = None
    method: str = ""
    failed: bool = False
    error: str = ""


@dataclass
class SearchQuery:
    query: str
    max_results: int = 6
    require_fresh: bool = False
    include_raw_content: bool = False
    topic: str = "general"          # "general" | "news"
    domains: List[str] = field(default_factory=list)


class SearchProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[RawSearchResult]:
        ...

    @abstractmethod
    async def extract(self, urls: List[str]) -> List[RawExtraction]:
        ...

    @abstractmethod
    async def aclose(self) -> None:
        ...
