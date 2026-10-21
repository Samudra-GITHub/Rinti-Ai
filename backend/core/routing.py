"""Which provider and model answer a request.

Deliberately transparent and rule-based (no classifier model): every decision
carries a plain-language `reason` that is reported to the client and logged, so
routing can be inspected and measured before anything cleverer is added.

Modes
  local  strict local-only: conversations never leave this machine; if the
         local model fails the user is told why, with no cloud fallback.
  auto   local first. If the local model fails *before* producing output, fall
         back to the cloud provider (when one is configured). Optionally
         (RINTI_CLOUD_ESCALATION) send unusually demanding prompts to the cloud.
  cloud  cloud only (the original behaviour).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import memory.database as db
from config import settings
from providers.base import (
    ModelUnavailable,
    PolicyViolation,
    ProviderUnavailable,
)
from core import local_fit
from providers.registry import cloud_providers, get_provider, providers

MODES = ("local", "auto", "cloud")


@dataclass(frozen=True)
class Target:
    provider: str
    model: str

    @property
    def kind(self) -> str:
        return get_provider(self.provider).kind


@dataclass(frozen=True)
class Route:
    primary: Target
    fallback: Optional[Target]
    reason: str
    task: str  # "coding" | "general"
    mode: str


@dataclass(frozen=True)
class InferenceConfig:
    mode: str
    local_model: str
    coding_model: str
    fast_model: str
    cloud_provider: str
    cloud_model: str
    escalation: bool
    # Whether "auto" may use the cloud when local can't answer. Separate from the
    # mode so Auto can also mean "pick the best local setup, never the cloud".
    cloud_fallback: bool = True


def default_mode() -> str:
    if settings.default_provider == "ollama":
        return "auto" if settings.cloud_fallback else "local"
    return "cloud"


_config_cache: tuple[float, InferenceConfig] | None = None


def _as_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes")


def load_config(force: bool = False) -> InferenceConfig:
    """Environment defaults overlaid with admin changes stored in the database."""
    global _config_cache
    now = time.monotonic()
    if not force and _config_cache and now - _config_cache[0] < 2:
        return _config_cache[1]
    try:
        stored = db.get_app_config()
    except Exception:  # noqa: BLE001 - config must never take the app down
        stored = {}
    mode = stored.get("inference_mode", default_mode())
    if mode not in MODES:
        mode = default_mode()
    local_model = stored.get("local_model") or settings.default_model
    cfg = InferenceConfig(
        mode=mode,
        local_model=local_model,
        coding_model=stored.get("coding_model") or settings.coding_model or local_model,
        fast_model=settings.fast_model or local_model,
        cloud_provider=stored.get("cloud_provider") or "groq",
        cloud_model=stored.get("cloud_model") or settings.cloud_model,
        escalation=settings.cloud_escalation,
        cloud_fallback=_as_bool(stored.get("cloud_fallback"), settings.cloud_fallback),
    )
    _config_cache = (now, cfg)
    return cfg


def invalidate_config_cache() -> None:
    global _config_cache
    _config_cache = None


# --- task classification ------------------------------------------------------

_CODE_FENCE = re.compile(r"```|~~~")
_TRACEBACK = re.compile(r"traceback \(most recent|stack ?trace|exception in thread|at \w+\.\w+\(.*:\d+\)|error TS\d+", re.I)
_CODE_VERB = re.compile(
    r"\b(debug|refactor|implement|fix (?:the|this|my)|write (?:a|an|the|some) (?:function|script|class|query|regex|program|test)|"
    r"unit tests?|compile|compiler|syntax error|runtime error|type ?error|null pointer|segfault|stack overflow)\b",
    re.I,
)
# Terms that almost always mean programming (languages, runtimes, tools)...
_TECH_STRONG = re.compile(
    r"\b(python|javascript|typescript|java|c\+\+|c#|rust|golang|php|ruby|kotlin|swift|sql|bash|powershell|"
    r"html|css|react|next\.?js|node\.?js|fastapi|django|flask|docker|kubernetes|git|regex|npm|pip|"
    r"algorithm|compiler|json|yaml)\b",
    re.I,
)
# ...and ordinary words that only suggest it in company.
_TECH_WEAK = re.compile(
    r"\b(function|variable|loop|array|list|class|method|library|package|api|code|script|query|syntax)\b", re.I
)
_CODE_CHARS = re.compile(r"[{};]|=>|\bdef \w+\(|\bfunction \w+\(|\bconst \w+ =|\bimport \w+|#include")


def classify_task(text: str) -> str:
    """"coding" for programming requests, otherwise "general"."""
    if _CODE_FENCE.search(text) or _TRACEBACK.search(text):
        return "coding"
    strong = len(set(m.lower() for m in _TECH_STRONG.findall(text)))
    weak = len(_TECH_WEAK.findall(text))
    verbs = bool(_CODE_VERB.search(text))
    if strong >= 2:
        return "coding"
    if strong >= 1 and (verbs or weak >= 1 or _CODE_CHARS.search(text)):
        return "coding"
    if verbs and weak >= 1:
        return "coding"
    if weak >= 3:
        return "coding"
    return "general"


_HARD = re.compile(
    r"\b(prove|proof|derive|derivation|rigorous|formally|trade-?offs?|architect(?:ure)?|"
    r"analy[sz]e in depth|step[- ]by[- ]step (?:proof|derivation)|optimi[sz]e the)\b",
    re.I,
)


def is_demanding(text: str) -> bool:
    return len(text) > 1800 or bool(_HARD.search(text))


# --- decision -------------------------------------------------------------------

def _installed_local() -> List[str]:
    return list(providers()["ollama"].installed_model_ids())  # type: ignore[attr-defined]


def _suitable_local_model(preferred: str) -> str:
    """The configured model if it fits this machine; otherwise the best installed
    catalogue model that does. Falls back to the configured one when unsure."""
    try:
        verdict = local_fit.assess_model(preferred)
        if verdict is None or verdict["fits"]:
            return preferred
        rec = local_fit.catalog.recommend(
            local_fit.hardware.detect(), _installed_local(), settings.commercial_use, settings.local_num_ctx
        )["recommended"]
        if rec and rec["installed"]:
            return rec["model"]
    except Exception:  # noqa: BLE001 - never block chat on a detection problem
        pass
    return preferred


def plan_route(user_text: str, requested_model: Optional[str] = None) -> Route:
    """Chooses where a request runs. Raises a ProviderError subclass (with a
    user-safe message) when the request can't be satisfied under the policy."""
    cfg = load_config()
    cloud = cloud_providers().get(cfg.cloud_provider)
    cloud_ready = bool(cloud and cloud.is_configured())
    cloud_target = Target(cfg.cloud_provider, cfg.cloud_model) if cloud_ready else None
    task = classify_task(user_text)
    requested = (requested_model or "auto").strip()

    # Cloud is only ever a fallback when Auto is on AND the fallback is enabled.
    fallback_target = cloud_target if (cfg.mode == "auto" and cfg.cloud_fallback) else None

    # 1. An explicit model choice wins, but never past the privacy policy.
    if requested != "auto":
        if requested in _installed_local():
            local_fit.ensure_runnable(requested)
            return Route(Target("ollama", requested), fallback_target, f"you selected {requested}", task, cfg.mode)
        if requested == cfg.cloud_model or (cloud and requested == getattr(cloud, "default_model", None)):
            if cfg.mode == "local" or (cfg.mode == "auto" and not cfg.cloud_fallback):
                raise PolicyViolation(
                    "Cloud models are turned off in the current mode. Choose a local model, "
                    "or change the mode or enable the cloud fallback in Settings."
                )
            if not cloud_target:
                raise ProviderUnavailable("No cloud provider is configured on the server.")
            return Route(cloud_target, None, f"you selected {requested}", task, cfg.mode)
        raise ModelUnavailable(f"The model '{requested}' isn't available. Pick another in the model menu.")

    # 2. Cloud-only mode: the original behaviour.
    if cfg.mode == "cloud":
        if not cloud_target:
            raise ProviderUnavailable("Cloud inference is selected but no API key is configured on the server.")
        return Route(cloud_target, None, "cloud mode", task, cfg.mode)

    # 3. Local or auto: rules choose the local model first.
    local_model = cfg.coding_model if task == "coding" else cfg.local_model
    why = "coding request, using the coding model" if (task == "coding" and cfg.coding_model != cfg.local_model) else (
        "coding request" if task == "coding" else "general request"
    )

    if cfg.mode == "auto":
        # Auto picks the best *local* setup for this machine. Moving from one
        # local model to another sends nothing off the computer.
        adapted = _suitable_local_model(local_model)
        if adapted != local_model:
            why = f"{local_model} doesn't suit this computer, so using {adapted}"
            local_model = adapted
    local_target = Target("ollama", local_model)

    if cfg.mode == "auto" and cfg.escalation and fallback_target and is_demanding(user_text):
        return Route(fallback_target, local_target, "demanding request escalated to the cloud model", task, cfg.mode)

    # Strict local mode: a model that can't fit is explained, never worked around.
    # Auto: only blocks if no local model is suitable and no fallback is enabled.
    if cfg.mode == "local" or not fallback_target:
        local_fit.ensure_runnable(local_model)
    return Route(local_target, fallback_target, f"{why}, local model", task, cfg.mode)


def status_snapshot() -> Dict[str, object]:
    """Read-only description of current routing for the UI (no secrets, no URLs)."""
    cfg = load_config()
    return {
        "mode": cfg.mode,
        "defaults": {
            "mode": default_mode(),
            "local_model": settings.default_model,
        },
        "local_model": cfg.local_model,
        "coding_model": cfg.coding_model,
        "cloud_provider": cfg.cloud_provider,
        "cloud_model": cfg.cloud_model,
        "cloud_escalation": cfg.escalation,
        "cloud_fallback": cfg.cloud_fallback,
    }
