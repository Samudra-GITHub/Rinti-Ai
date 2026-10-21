"""Ollama adapter (local models) using Ollama's native /api/chat.

Why native rather than its OpenAI-compatible endpoint: only the native API
accepts `options.num_ctx` (the context window actually allocated), `keep_alive`
and reports load/eval timings. Closing the HTTP stream makes Ollama stop
generating, which is how the Stop button cancels a local reply.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx2 as httpx  # the HTTP client this project (and the openai SDK) already depends on

from config import settings
from providers.base import (
    GenParams,
    LLMProvider,
    Message,
    ModelInfo,
    ModelUnavailable,
    ProviderError,
    ProviderHealth,
    ProviderTimeout,
    ProviderUnavailable,
    StreamEvent,
)

# Reasoning models (qwen3, deepseek-r1, gpt-oss) return their reasoning in a
# separate `thinking` field. We only ever read `content`, so it never reaches
# the user. (Do NOT send `think: false`: on current Ollama builds that makes
# qwen3 write its reasoning into `content` instead.)

_UNAVAILABLE = (
    "The local model server (Ollama) isn't reachable. Start Ollama, or switch to a cloud model in Settings."
)


def _missing_model(model: str) -> ModelUnavailable:
    return ModelUnavailable(f"The local model '{model}' isn't installed. Install it with: ollama pull {model}")


class OllamaProvider(LLMProvider):
    name = "ollama"
    label = "Ollama (local)"
    kind = "local"

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._tags_cache: tuple[float, ProviderHealth] | None = None
        self._show_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}

    # -- configuration -------------------------------------------------------
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def context_limit(self, model: str) -> int:
        return settings.local_num_ctx

    def _payload(self, messages: List[Message], model: str, params: GenParams, stream: bool) -> Dict[str, Any]:
        options: Dict[str, Any] = {
            "temperature": params.temperature,
            "num_ctx": params.num_ctx or settings.local_num_ctx,
        }
        if params.max_tokens:
            options["num_predict"] = params.max_tokens
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options,
            "keep_alive": settings.ollama_keep_alive,
        }
        if params.json_mode:
            payload["format"] = "json"
        return payload

    # -- error mapping -------------------------------------------------------
    @staticmethod
    def _raise_for_status(response: httpx.Response, model: str) -> None:
        if response.status_code == 404:
            raise _missing_model(model)
        if response.status_code >= 400:
            raise ProviderError("The local model server returned an error. Check the Ollama logs.", retryable=True)

    @staticmethod
    def _raise_for_error_text(text: str, model: str) -> None:
        lowered = text.lower()
        if "not found" in lowered or "pull" in lowered:
            raise _missing_model(model)
        if "memory" in lowered:
            raise ProviderError("The local model needs more memory than is free. Try a smaller model.")
        raise ProviderError("The local model failed to generate a reply.", retryable=True)

    # -- inference -----------------------------------------------------------
    async def stream(self, messages: List[Message], model: str, params: GenParams) -> AsyncIterator[StreamEvent]:
        timeout = httpx.Timeout(10.0, read=settings.request_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=self._payload(messages, model, params, True)
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        self._raise_for_status(response, model)
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except ValueError:
                            continue
                        if "error" in chunk:
                            self._raise_for_error_text(str(chunk["error"]), model)
                        text = (chunk.get("message") or {}).get("content") or ""
                        if text:
                            yield StreamEvent("text", text=text)
                        if chunk.get("done"):
                            yield StreamEvent(
                                "usage",
                                usage={
                                    "prompt_tokens": chunk.get("prompt_eval_count"),
                                    "completion_tokens": chunk.get("eval_count"),
                                    "load_seconds": (chunk.get("load_duration") or 0) / 1e9,
                                    "total_seconds": (chunk.get("total_duration") or 0) / 1e9,
                                },
                            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailable(_UNAVAILABLE) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("The local model took too long to respond.", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(_UNAVAILABLE) from exc

    def complete(self, messages: List[Message], model: str, params: GenParams) -> str:
        timeout = httpx.Timeout(10.0, read=settings.request_timeout_seconds)
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat", json=self._payload(messages, model, params, False), timeout=timeout
            )
        except httpx.ConnectError as exc:
            raise ProviderUnavailable(_UNAVAILABLE) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("The local model took too long to respond.", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(_UNAVAILABLE) from exc
        self._raise_for_status(response, model)
        body = response.json()
        if "error" in body:
            self._raise_for_error_text(str(body["error"]), model)
        return (body.get("message") or {}).get("content") or ""

    # -- health / discovery --------------------------------------------------
    def health(self) -> ProviderHealth:
        """Reachability plus installed and currently loaded models. Cached ~5s."""
        now = time.monotonic()
        if self._tags_cache and now - self._tags_cache[0] < 5:
            return self._tags_cache[1]
        try:
            tags = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            tags.raise_for_status()
            models = []
            for item in tags.json().get("models", []):
                details = item.get("details") or {}
                models.append(
                    ModelInfo(
                        id=item.get("name", ""),
                        provider=self.name,
                        size_bytes=item.get("size"),
                        parameter_size=details.get("parameter_size"),
                        quantization=details.get("quantization_level"),
                        family=details.get("family"),
                    )
                )
            loaded: List[Dict[str, Any]] = []
            try:
                ps = httpx.get(f"{self.base_url}/api/ps", timeout=2.0)
                for item in ps.json().get("models", []):
                    loaded.append(
                        {
                            "model": item.get("name"),
                            "size_bytes": item.get("size"),
                            "vram_bytes": item.get("size_vram"),
                            "context": item.get("context_length"),
                        }
                    )
            except (httpx.HTTPError, ValueError):
                pass
            result = ProviderHealth(True, f"{len(models)} model(s) installed", models, loaded)
        except (httpx.HTTPError, ValueError):
            result = ProviderHealth(False, "Ollama isn't reachable")
        self._tags_cache = (now, result)
        return result

    def installed_model_ids(self) -> List[str]:
        return [m.id for m in self.health().models]

    def show(self, model: str) -> Dict[str, Any]:
        """Facts stored in the model file: licence text and architecture. Cached
        10 minutes (they never change for an installed model); {} if unavailable."""
        now = time.monotonic()
        cached = self._show_cache.get(model)
        if cached and now - cached[0] < 600:
            return cached[1]
        try:
            response = httpx.post(f"{self.base_url}/api/show", json={"model": model}, timeout=5.0)
            response.raise_for_status()
            body = response.json()
            info = {"license": body.get("license") or "", "model_info": body.get("model_info") or {}}
        except (httpx.HTTPError, ValueError):
            return {}
        self._show_cache[model] = (now, info)
        return info
