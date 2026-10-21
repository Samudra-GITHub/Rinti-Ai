"""The one entry point the application uses to run a model.

Callers hand over OpenAI-style messages and (for chat) a `Route` produced by
`routing.plan_route`; this module applies the context budget, enforces
concurrency and timeout limits, streams from the chosen provider, and falls
back to the route's fallback target only when that is allowed and only if the
primary failed before producing any text. Nothing here logs message content.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import AsyncIterator, Dict, List, Optional

from config import settings
from core import local_fit
from core.context import fit_messages
from core.routing import Route, Target, plan_route
from providers.base import (
    GenParams,
    Message,
    ProviderBusy,
    ProviderError,
    ProviderTimeout,
    StreamEvent,
)
from providers.registry import get_provider

# --- concurrency limits ---------------------------------------------------------

_async_limiters: Dict[str, asyncio.Semaphore] = {}
_sync_limiters: Dict[str, threading.BoundedSemaphore] = {}


def _limit_for(kind: str) -> int:
    return max(1, settings.local_max_concurrency if kind == "local" else settings.cloud_max_concurrency)


def _async_limiter(kind: str) -> asyncio.Semaphore:
    if kind not in _async_limiters:
        _async_limiters[kind] = asyncio.Semaphore(_limit_for(kind))
    return _async_limiters[kind]


def _sync_limiter(kind: str) -> threading.BoundedSemaphore:
    if kind not in _sync_limiters:
        _sync_limiters[kind] = threading.BoundedSemaphore(_limit_for(kind))
    return _sync_limiters[kind]


_BUSY = ProviderBusy("Rinti is busy finishing another reply. Try again in a moment.", retryable=True)


def _params(kind: str, *, temperature: float, max_tokens: Optional[int], json_mode: bool, model: str = "") -> GenParams:
    if kind == "local":
        cap = settings.local_max_response_tokens
        return GenParams(
            temperature=temperature,
            max_tokens=min(max_tokens, cap) if max_tokens else cap,
            json_mode=json_mode,
            # The configured window, lowered if this machine can't hold it for this model.
            num_ctx=local_fit.effective_context(model) if model else settings.local_num_ctx,
        )
    return GenParams(
        temperature=temperature,
        max_tokens=max_tokens or settings.max_response_tokens,
        json_mode=json_mode,
    )


def _prepare(messages: List[Message], target: Target, params: GenParams) -> tuple[List[Message], int]:
    provider = get_provider(target.provider)
    limit = params.num_ctx or provider.context_limit(target.model)
    return fit_messages(messages, limit, reserve_tokens=params.max_tokens or 1024)


# --- streaming chat -------------------------------------------------------------

async def stream_chat(
    route: Route, messages: List[Message], *, temperature: float = 0.7
) -> AsyncIterator[StreamEvent]:
    """Yields a "meta" event (which provider/model is answering), then "text"
    events, then possibly a "usage" event. Raises ProviderError on failure."""
    targets = [route.primary] + ([route.fallback] if route.fallback else [])
    emitted_text = False

    for index, target in enumerate(targets):
        provider = get_provider(target.provider)
        params = _params(provider.kind, temperature=temperature, max_tokens=None, json_mode=False, model=target.model)
        fitted, dropped = _prepare(messages, target, params)
        reason = route.reason if index == 0 else "fell back to the cloud model because the local model failed"
        yield StreamEvent(
            "meta",
            usage={
                "provider": provider.name,
                "model": target.model,
                "kind": provider.kind,
                "reason": reason,
                "task": route.task,
                "mode": route.mode,
                "dropped_messages": dropped,
            },
        )

        limiter = _async_limiter(provider.kind)
        try:
            await asyncio.wait_for(limiter.acquire(), timeout=settings.queue_timeout_seconds)
        except asyncio.TimeoutError:
            if index == len(targets) - 1:
                raise _BUSY from None
            continue

        try:
            async with asyncio.timeout(settings.request_timeout_seconds):
                async for event in provider.stream(fitted, target.model, params):
                    if event.kind == "text":
                        emitted_text = True
                    yield event
            return
        except TimeoutError:
            error: ProviderError = ProviderTimeout("The model took too long to respond.", retryable=True)
        except ProviderError as exc:
            error = exc
        finally:
            limiter.release()

        # Only reached when the attempt failed.
        print(f"[inference] {provider.name}/{target.model} failed: {error.code}")
        if emitted_text or index == len(targets) - 1:
            raise error
        # otherwise: nothing was shown to the user yet, so try the fallback target


# --- blocking completion (research, classification, non-streaming chat) ---------

@dataclass
class Completion:
    text: str
    provider: str
    model: str


def complete_sync(
    messages: List[Message],
    *,
    purpose: str = "chat",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    json_mode_cloud: Optional[bool] = None,
    requested_model: Optional[str] = None,
    user_text: Optional[str] = None,
) -> Completion:
    """Runs one completion under the same routing policy as chat. `purpose`
    "classify" uses the (optional) fast local model. Research calls pass
    through here too, so strict local-only mode covers them as well.

    `json_mode_cloud` overrides `json_mode` for cloud providers only (None = same
    as `json_mode`): lets a call keep its original cloud request unchanged while
    local models get constrained JSON output."""
    text_for_routing = user_text if user_text is not None else next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    route = plan_route(text_for_routing, requested_model)
    if purpose == "classify" and route.primary.provider == "ollama":
        # Only an explicitly configured fast model replaces the routed one. Defaulting to
        # the configured everyday model would bypass the hardware-aware choice made above.
        fast = settings.fast_model
        if fast and fast != route.primary.model:
            local_fit.ensure_runnable(fast)
            route = Route(Target("ollama", fast), route.fallback, "classification, fast model", route.task, route.mode)

    targets = [route.primary] + ([route.fallback] if route.fallback else [])
    last_error: Optional[ProviderError] = None
    for index, target in enumerate(targets):
        provider = get_provider(target.provider)
        use_json = json_mode_cloud if (provider.kind == "cloud" and json_mode_cloud is not None) else json_mode
        params = _params(provider.kind, temperature=temperature, max_tokens=max_tokens, json_mode=use_json, model=target.model)
        fitted, _ = _prepare(messages, target, params)
        limiter = _sync_limiter(provider.kind)
        if not limiter.acquire(timeout=settings.queue_timeout_seconds):
            last_error = _BUSY
            continue
        started = time.monotonic()
        try:
            text = provider.complete(fitted, target.model, params)
            print(f"[inference] {purpose}: {provider.name}/{target.model} {time.monotonic() - started:.1f}s")
            return Completion(text, provider.name, target.model)
        except ProviderError as exc:
            last_error = exc
            print(f"[inference] {provider.name}/{target.model} failed: {exc.code}")
        finally:
            limiter.release()
    raise last_error or ProviderError("No model is available to answer this request.")
