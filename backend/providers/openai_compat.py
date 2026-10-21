"""Adapter for any OpenAI-compatible chat API (Groq by default, OpenRouter,
Together, a self-hosted vLLM, ...). Clients are created lazily, so the
application starts and runs without any cloud key when only local inference
is used."""

from __future__ import annotations

from typing import AsyncIterator, List, Optional

import httpx2 as httpx  # the HTTP client this project (and the openai SDK) already depends on
import openai
from openai import AsyncOpenAI, OpenAI

from config import settings
from providers.base import (
    GenParams,
    LLMProvider,
    Message,
    ModelInfo,
    ModelUnavailable,
    ProviderAuthError,
    ProviderError,
    ProviderHealth,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
    StreamEvent,
)


def _translate(exc: Exception, label: str, model: str) -> ProviderError:
    """Map an SDK exception to a user-safe ProviderError (never echo the SDK text,
    which can include masked key fragments)."""
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return ProviderAuthError(f"{label} rejected the API key. Check the key configured on the server.")
    if isinstance(exc, openai.RateLimitError):
        return ProviderRateLimited(f"{label} is rate limiting requests right now. Try again shortly.", retryable=True)
    if isinstance(exc, openai.APITimeoutError):
        return ProviderTimeout(f"{label} took too long to respond.", retryable=True)
    if isinstance(exc, openai.APIConnectionError):
        return ProviderUnavailable(f"{label} can't be reached from the server.", retryable=True)
    if isinstance(exc, openai.NotFoundError):
        return ModelUnavailable(f"{label} doesn't offer the model '{model}'.")
    return ProviderError(f"{label} returned an error. Please try again.", retryable=True)


class OpenAICompatProvider(LLMProvider):
    kind = "cloud"

    def __init__(self, name: str, label: str, base_url: Optional[str], api_key: str, default_model: str):
        self.name = name
        self.label = label
        self.base_url = base_url or None
        self._api_key = api_key
        self.default_model = default_model
        self._sync: OpenAI | None = None
        self._async: AsyncOpenAI | None = None

    def is_configured(self) -> bool:
        return bool(self._api_key.strip())

    def context_limit(self, model: str) -> int:
        return settings.cloud_context_tokens

    def _sync_client(self) -> OpenAI:
        if self._sync is None:
            self._sync = OpenAI(
                api_key=self._api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(10.0, read=settings.request_timeout_seconds),
                max_retries=1,
            )
        return self._sync

    def _async_client(self) -> AsyncOpenAI:
        if self._async is None:
            self._async = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(10.0, read=settings.request_timeout_seconds),
                max_retries=1,
            )
        return self._async

    def _kwargs(self, messages: List[Message], model: str, params: GenParams) -> dict:
        kwargs: dict = {"model": model, "messages": messages, "temperature": params.temperature}
        if params.max_tokens:
            kwargs["max_tokens"] = params.max_tokens
        if params.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    async def stream(self, messages: List[Message], model: str, params: GenParams) -> AsyncIterator[StreamEvent]:
        try:
            stream = await self._async_client().chat.completions.create(
                **self._kwargs(messages, model, params), stream=True
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                text = chunk.choices[0].delta.content or ""
                if text:
                    yield StreamEvent("text", text=text)
        except openai.OpenAIError as exc:
            raise _translate(exc, self.label, model) from exc

    def complete(self, messages: List[Message], model: str, params: GenParams) -> str:
        try:
            response = self._sync_client().chat.completions.create(**self._kwargs(messages, model, params))
        except openai.OpenAIError as exc:
            raise _translate(exc, self.label, model) from exc
        return response.choices[0].message.content or ""

    def health(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(False, "No API key configured")
        try:
            client = OpenAI(api_key=self._api_key, base_url=self.base_url, timeout=5.0, max_retries=0)
            client.models.list()
            return ProviderHealth(True, "Reachable", [ModelInfo(self.default_model, self.name)])
        except openai.OpenAIError as exc:
            return ProviderHealth(False, _translate(exc, self.label, self.default_model).user_message)
