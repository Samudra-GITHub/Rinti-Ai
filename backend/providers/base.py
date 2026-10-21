"""Provider-independent model interface.

Application code (routes, the chat brain, research) talks to `LLMProvider`
objects through this module only. Each provider adapter translates the shared
shapes below into its own wire format (OpenAI-compatible HTTP, Ollama's native
API, ...), so business logic never depends on a particular vendor.

Messages are plain OpenAI-style dicts: {"role": "system|user|assistant",
"content": "..."}. Every error a provider can raise is a `ProviderError`
carrying a stable `code` and a message that is safe to show to a user: no keys,
URLs or stack traces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

Message = Dict[str, str]


class ProviderError(Exception):
    """A failure from a model provider, with a user-safe explanation."""

    code = "provider_error"

    def __init__(self, user_message: str, *, retryable: bool = False):
        super().__init__(user_message)
        self.user_message = user_message
        self.retryable = retryable


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"


class ModelUnavailable(ProviderError):
    code = "model_unavailable"


class ProviderAuthError(ProviderError):
    code = "provider_auth"


class ProviderRateLimited(ProviderError):
    code = "rate_limited"


class ProviderTimeout(ProviderError):
    code = "provider_timeout"


class ProviderBusy(ProviderError):
    code = "provider_busy"


class PolicyViolation(ProviderError):
    """The request would break the configured policy (for example, a cloud model
    was requested while strict local-only mode is on)."""

    code = "policy_violation"


@dataclass
class GenParams:
    """Generation settings, expressed once and mapped per provider."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    json_mode: bool = False
    # Context window to request (local providers only; cloud models fix their own).
    num_ctx: Optional[int] = None


@dataclass
class StreamEvent:
    """One item of a streamed generation: a text delta or final usage numbers."""

    kind: str  # "text" | "usage"
    text: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    id: str
    provider: str
    size_bytes: Optional[int] = None
    parameter_size: Optional[str] = None
    quantization: Optional[str] = None
    family: Optional[str] = None


@dataclass
class ProviderHealth:
    reachable: bool
    detail: str = ""  # short, user-safe
    models: List[ModelInfo] = field(default_factory=list)
    loaded: List[Dict[str, Any]] = field(default_factory=list)  # models currently in memory


class LLMProvider(ABC):
    #: Stable identifier used in config and routing ("ollama", "groq", ...).
    name: str
    #: Human label for the UI.
    label: str
    #: "local" runs on this machine; "cloud" sends the conversation to a vendor.
    kind: str

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the provider has what it needs (a key, a base URL)."""

    @abstractmethod
    def stream(self, messages: List[Message], model: str, params: GenParams) -> AsyncIterator[StreamEvent]:
        """Async generator of StreamEvents. Closing/cancelling it must stop generation."""

    @abstractmethod
    def complete(self, messages: List[Message], model: str, params: GenParams) -> str:
        """Blocking, non-streaming completion returning the text."""

    @abstractmethod
    def health(self) -> ProviderHealth:
        """A quick, bounded reachability check (never raises)."""

    @abstractmethod
    def context_limit(self, model: str) -> int:
        """Token budget for one request to this model (prompt + reply)."""
