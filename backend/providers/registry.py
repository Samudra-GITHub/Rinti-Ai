"""Builds the set of configured providers from settings.

"ollama" is always available as an adapter (whether it is *reachable* is a
health question). The cloud provider "groq" is built from the legacy
OPENAI_API_KEY / OPENAI_BASE_URL variables. More OpenAI-compatible providers
can be declared with RINTI_EXTRA_PROVIDERS; their keys come from environment
variables named in that JSON, never from the JSON itself.
"""

from __future__ import annotations

import json
import os
from typing import Dict

from config import settings
from providers.base import LLMProvider
from providers.ollama import OllamaProvider
from providers.openai_compat import OpenAICompatProvider

_registry: Dict[str, LLMProvider] | None = None


def _build() -> Dict[str, LLMProvider]:
    providers: Dict[str, LLMProvider] = {
        "ollama": OllamaProvider(),
        "groq": OpenAICompatProvider(
            name="groq",
            label="Groq (cloud)",
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            default_model=settings.cloud_model,
        ),
    }
    if settings.extra_providers.strip():
        try:
            for item in json.loads(settings.extra_providers):
                name = str(item["name"]).strip().lower()
                if not name or name in providers:
                    continue
                providers[name] = OpenAICompatProvider(
                    name=name,
                    label=f"{item.get('label') or name} (cloud)",
                    base_url=item.get("base_url"),
                    api_key=os.getenv(str(item.get("api_key_env", "")), ""),
                    default_model=str(item.get("model", "")),
                )
        except (ValueError, KeyError, TypeError):
            # A malformed value must not stop the app; the built-in providers still work.
            print("[providers] RINTI_EXTRA_PROVIDERS is not valid JSON; ignoring it")
    return providers


def providers() -> Dict[str, LLMProvider]:
    global _registry
    if _registry is None:
        _registry = _build()
    return _registry


def get_provider(name: str) -> LLMProvider:
    try:
        return providers()[name]
    except KeyError:
        raise KeyError(f"unknown provider '{name}'") from None


def cloud_providers() -> Dict[str, LLMProvider]:
    return {n: p for n, p in providers().items() if p.kind == "cloud"}
