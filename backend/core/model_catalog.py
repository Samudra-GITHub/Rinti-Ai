"""Which local models suit which machine, and under which licence.

Pure functions (no network, no process state) so they can be tested with made-up
hardware. Inputs are a `Hardware` description and model facts; outputs are plain
dicts for the API.

Two kinds of facts, kept apart on purpose:
  * VERIFIED_MODELS: the short list Rinti has benchmarked or whose licence and
    size were checked against the publisher's own pages (see docs/LOCAL_INFERENCE.md,
    "Model catalogue"). Only these are ever *recommended*.
  * Any other installed model: described from what Ollama reports about the
    file itself (size, parameters, the licence text shipped in the model), with
    its licence classified from that text. Never recommended automatically.

Memory figures are ESTIMATES (weights + KV cache + a fixed overhead), checked
against one measurement on the development machine; they say "should fit", not
"was tested here".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.hardware import Hardware

# Context sizes Rinti will ask Ollama for, largest first.
CTX_CHOICES = (8192, 4096, 2048)
# Below this the system prompt, memory notes and an answer barely fit.
MIN_USABLE_CTX = 4096
# Allocation overhead (compute buffers, runtime) on top of weights + KV cache.
OVERHEAD_GB = 0.35
# Share of video memory Ollama can really use for one model (the rest goes to the
# desktop, the driver and its own buffers). Calibrated on ONE machine: on a 6 GB
# RTX 4050 a 3.9 GB model loaded 100% on the GPU while a 5.4 GB model got 4.1 GB.
GPU_SHARE = 0.75
RAM_SHARE = 0.70
# On CPU only, larger models are too slow for chat (see docs for the measurement).
CPU_ONLY_MAX_PARAMS_B = 4.0
# A model above that size is only called a workable GPU/CPU split on a card at
# least as large as the one it was tested on (6 GB). On a smaller card most of it
# would run on the CPU, which was too slow when measured.
TESTED_SPLIT_VRAM_GB = 5.5


@dataclass(frozen=True)
class CatalogModel:
    id: str
    label: str
    params_b: float
    download_gb: float
    kv_bytes_per_token: int  # fallback when Ollama doesn't report model_info
    license_id: str
    license_name: str
    license_url: str
    commercial: str  # "yes" | "no" | "review"
    tested: str  # what Rinti actually measured, in words
    role: str


# Ordered best-first. Sizes: Ollama library pages (checked 2026-10-21).
# Licences: publisher pages and the licence text shipped in the model (see docs).
VERIFIED_MODELS: List[CatalogModel] = [
    CatalogModel(
        id="qwen2.5:7b",
        label="Qwen2.5 7B",
        params_b=7.6,
        download_gb=4.7,
        kv_bytes_per_token=57344,
        license_id="apache-2.0",
        license_name="Apache License 2.0",
        license_url="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct",
        commercial="yes",
        tested="Benchmarked on RTX 4050 6 GB: 0 of 28 runs failed, 37/38 correctness checks.",
        role="Everyday and coding default for machines with a 6 GB+ GPU or 16 GB+ RAM",
    ),
    CatalogModel(
        id="phi4-mini",
        label="Phi-4 mini 3.8B",
        params_b=3.8,
        download_gb=2.5,
        kv_bytes_per_token=131072,
        license_id="mit",
        license_name="MIT License",
        license_url="https://huggingface.co/microsoft/Phi-4-mini-instruct",
        commercial="yes",
        tested=(
            "Benchmarked: 0 of 28 runs failed, 35/38 correctness, 22/22 instruction, 38/40 style. "
            "59 tokens/s on a GPU; 13.6 tokens/s on one laptop CPU. Often omits [n] citations in research answers."
        ),
        role="Smaller machines (about 4 GB GPU or 8 GB RAM)",
    ),
    CatalogModel(
        id="qwen2.5:1.5b",
        label="Qwen2.5 1.5B",
        params_b=1.5,
        download_gb=0.99,
        kv_bytes_per_token=28672,
        license_id="apache-2.0",
        license_name="Apache License 2.0",
        license_url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct",
        commercial="yes",
        tested=(
            "Benchmarked: 0 of 28 runs failed but only 31/38 correctness: it got a change calculation wrong, "
            "wrote incorrect code and missed a debugging answer. Basic chat only."
        ),
        role="Very weak machines; basic chat only, expect clear quality limits",
    ),
]

_CATALOG_BY_ID = {m.id: m for m in VERIFIED_MODELS}


def catalog_entry(model_id: str) -> Optional[CatalogModel]:
    base = model_id.split(":latest")[0]
    return _CATALOG_BY_ID.get(base)


# --- licences --------------------------------------------------------------------

def classify_license(text: Optional[str]) -> Dict[str, str]:
    """Identify a licence from the text Ollama ships inside the model file.

    Conservative: anything not clearly permissive is "review", never "yes".
    """
    if not text or not text.strip():
        return {"id": "unknown", "name": "No licence text found in the model", "commercial": "review"}
    t = " ".join(text.split())
    low = t.lower()
    if "qwen research license" in low:
        return {"id": "qwen-research", "name": "Qwen Research License (non-commercial)", "commercial": "no"}
    if "apache license" in low and "version 2.0" in low:
        return {"id": "apache-2.0", "name": "Apache License 2.0", "commercial": "yes"}
    if "permission is hereby granted, free of charge" in low and "mit license" in low:
        return {"id": "mit", "name": "MIT License", "commercial": "yes"}
    if "qwen license agreement" in low:
        return {"id": "qwen", "name": "Qwen License Agreement (custom terms)", "commercial": "review"}
    if "gemma" in low and "terms of use" in low:
        return {"id": "gemma", "name": "Gemma Terms of Use (use restrictions apply)", "commercial": "review"}
    if "llama" in low and "community license" in low:
        return {"id": "llama-community", "name": "Llama Community License (conditions apply)", "commercial": "review"}
    return {"id": "custom", "name": "Custom licence: read it before deploying", "commercial": "review"}


# --- memory estimates ------------------------------------------------------------

def kv_bytes_per_token(model_info: Optional[Dict[str, Any]], fallback: Optional[int] = None) -> Optional[int]:
    """Bytes of KV cache per token (f16), from Ollama's /api/show model_info."""
    if model_info:
        def find(suffix: str) -> Optional[int]:
            for key, value in model_info.items():
                if key.endswith(suffix) and isinstance(value, (int, float)):
                    return int(value)
            return None

        layers = find(".block_count")
        heads = find(".attention.head_count")
        kv_heads = find(".attention.head_count_kv") or heads
        embed = find(".embedding_length")
        head_dim = find(".attention.key_length") or (embed // heads if embed and heads else None)
        if layers and kv_heads and head_dim:
            return 2 * layers * kv_heads * head_dim * 2
    return fallback


def estimate_memory_gb(weights_gb: float, kv_per_token: Optional[int], ctx: int) -> float:
    kv_gb = (kv_per_token or 131072) * ctx / 1024**3  # unknown models: assume a heavy cache
    return round(weights_gb + kv_gb + OVERHEAD_GB, 2)


# --- fit -------------------------------------------------------------------------

def _gpu_budget(hw: Hardware) -> float:
    return hw.gpu.vram_total_gb * GPU_SHARE if hw.gpu else 0.0


def assess(hw: Hardware, weights_gb: float, params_b: Optional[float], kv_per_token: Optional[int], ctx: int) -> Dict[str, Any]:
    """How a model of this size will run here.

    level
      gpu      fits in video memory: fast
      partial  split between GPU and RAM: works, slower (what a 6 GB card does with 7B)
      cpu      CPU only: slow, small models only
      no       too large for this machine's memory
    """
    needed = estimate_memory_gb(weights_gb, kv_per_token, ctx)
    ram_budget = hw.ram_total_gb * RAM_SHARE
    ram_ok = needed <= ram_budget
    reasons: List[str] = []

    big = bool(params_b and params_b > CPU_ONLY_MAX_PARAMS_B)
    if hw.gpu and needed <= _gpu_budget(hw):
        level = "gpu"
    elif hw.gpu and ram_ok and hw.gpu.vram_total_gb >= 3.5 and hw.gpu.source != "apple-silicon":
        if big and hw.gpu.vram_total_gb < TESTED_SPLIT_VRAM_GB:
            level = "no"
            reasons.append(
                f"A {params_b:g}B model on a {hw.gpu.vram_total_gb:g} GB graphics card would mostly run on the CPU, "
                "which was too slow when tested. Use a smaller model or the cloud."
            )
        else:
            level = "partial"
            reasons.append("The model is larger than video memory, so part of it runs on the CPU. Replies are slower.")
    elif hw.gpu and hw.gpu.source == "apple-silicon" and ram_ok:
        level = "partial"
    elif ram_ok:
        level = "cpu"
        reasons.append(
            "There's no usable GPU, so the model runs on the CPU. Replies are slower, and the first reply "
            "in a conversation can take tens of seconds."
        )
        if params_b and params_b > CPU_ONLY_MAX_PARAMS_B:
            level = "no"
            reasons = [
                f"A {params_b:g}B model is too slow on a CPU for comfortable chat. Use a smaller model or the cloud."
            ]
    else:
        level = "no"
        reasons = [
            f"It needs about {needed:.1f} GB and this machine has {hw.ram_total_gb:g} GB of memory "
            f"(about {ram_budget:.1f} GB is usable for a model)."
        ]

    if level != "no" and hw.gpu and hw.gpu.source == "apple-silicon":
        reasons.append("Apple Silicon hasn't been tested with Rinti, so treat this as an estimate.")

    if level != "no" and hw.ram_available_gb is not None and level in ("partial", "cpu") and needed > hw.ram_available_gb - 0.5:
        reasons.append(f"Only {hw.ram_available_gb:g} GB of memory is free right now; close other programs first.")

    return {
        "level": level,
        "fits": level != "no",
        "needed_gb": needed,
        "context": ctx,
        "speed": {"gpu": "fast", "partial": "moderate", "cpu": "slow", "no": "not suitable"}[level],
        "reasons": reasons,
    }


def best_context(hw: Hardware, weights_gb: float, params_b: Optional[float], kv_per_token: Optional[int], cap: int) -> int:
    """Largest window that does not make the model run worse than at the smallest window."""
    choices = [c for c in CTX_CHOICES if c <= cap] or [min(CTX_CHOICES)]
    order = {"gpu": 3, "partial": 2, "cpu": 1, "no": 0}
    smallest = choices[-1]
    baseline = order[assess(hw, weights_gb, params_b, kv_per_token, smallest)["level"]]
    for ctx in choices:
        if order[assess(hw, weights_gb, params_b, kv_per_token, ctx)["level"]] >= baseline:
            return ctx
    return smallest


# --- recommendation --------------------------------------------------------------

def recommend(hw: Hardware, installed_ids: List[str], commercial_only: bool, ctx_cap: int = 8192) -> Dict[str, Any]:
    """Pick the best catalogue model that suits this machine.

    Never returns a model for commercial deployment unless its licence is
    permissive. Says plainly when nothing suitable exists.
    """
    candidates: List[Dict[str, Any]] = []
    chosen: Optional[Dict[str, Any]] = None
    for model in VERIFIED_MODELS:
        if commercial_only and model.commercial != "yes":
            continue
        ctx = best_context(hw, model.download_gb, model.params_b, model.kv_bytes_per_token, ctx_cap)
        result = assess(hw, model.download_gb, model.params_b, model.kv_bytes_per_token, ctx)
        entry = {
            "model": model.id,
            "label": model.label,
            "download_gb": model.download_gb,
            "installed": any(i == model.id or i == f"{model.id}:latest" for i in installed_ids),
            "context": ctx,
            "fit": result,
            "license": {"id": model.license_id, "name": model.license_name, "commercial": model.commercial, "url": model.license_url},
            "tested": model.tested,
            "role": model.role,
        }
        candidates.append(entry)
        # A usable chat needs a real window; CPU-only speed is "works", not "good".
        if chosen is None and result["fits"] and ctx >= MIN_USABLE_CTX:
            chosen = entry

    if chosen:
        summary = (
            f"{chosen['label']} suits this machine ({chosen['fit']['speed']}, {chosen['context']:,} token window)."
            + ("" if chosen["installed"] else f" Install it with `ollama pull {chosen['model']}`.")
        )
    else:
        summary = (
            "No local model in Rinti's verified list is a comfortable fit for this machine. "
            "Cloud mode is the better choice here, or choose a model yourself and accept slower replies."
        )
    return {"recommended": chosen, "candidates": candidates, "summary": summary, "commercial_only": commercial_only}
