"""Inference status and configuration.

Reading the status is open (it contains model names and health, never keys or
URLs). Changing settings is restricted: allowed from this machine (loopback),
or from anywhere with the RINTI_ADMIN_TOKEN in the X-Rinti-Admin header. There
is deliberately NO endpoint to download, delete or run arbitrary models:
installing models is done on the host with the Ollama CLI.
"""

from __future__ import annotations

import hmac
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

import memory.database as db
from auth.dependencies import get_current_user, verify_csrf_header
from config import settings
from core import hardware, local_fit, routing
from providers.registry import cloud_providers, providers

router = APIRouter()

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def require_admin(request: Request, x_rinti_admin: Optional[str] = Header(default=None)) -> None:
    """Authorizes configuration changes (see module docstring)."""
    if settings.admin_token:
        if x_rinti_admin and hmac.compare_digest(x_rinti_admin, settings.admin_token):
            return
        raise HTTPException(status_code=403, detail="Changing inference settings requires the admin token.")
    # On a hosted backend (Vercel, containers) every request arrives through the
    # platform's proxy, so "the client is local" can't be established from the
    # socket. Without a token nobody may change settings there.
    if hardware.deployment()["hosted"] or settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Inference settings can't be changed on a hosted deployment without an admin token.",
        )
    host = request.client.host if request.client else ""
    forwarded = request.headers.get("x-forwarded-for")
    # Behind a proxy the TCP peer is the proxy, so a forwarded header means "not local".
    if host in _LOOPBACK and not forwarded:
        return
    raise HTTPException(
        status_code=403,
        detail="Inference settings can only be changed from the machine running Rinti, or with an admin token.",
    )


class InferenceConfigUpdate(BaseModel):
    mode: Optional[str] = None  # local | auto | cloud
    local_model: Optional[str] = None
    coding_model: Optional[str] = None
    cloud_model: Optional[str] = None
    cloud_fallback: Optional[bool] = None  # Auto only: may the cloud answer if local can't?


def _assessment(snapshot: Dict[str, Any], reachable: bool, overview: Dict[str, Any]) -> Dict[str, Any]:
    """Is the current local setup usable here? If not, what the user can choose to do.
    These are suggestions only; nothing is switched automatically."""
    model_id = snapshot["local_model"]
    entry = next((m for m in overview["models"] if m["id"] == model_id or m["id"] == f"{model_id}:latest"), None)
    problems: List[str] = []
    notes: List[str] = []
    level = "good"
    if not reachable:
        level = "unavailable"
        problems.append("Ollama isn't running on the computer that hosts Rinti.")
    elif entry is None:
        level = "unavailable"
        problems.append(f"{model_id} isn't installed.")
    elif entry["fit"] and not entry["fit"]["fits"]:
        level = "unsuitable"
        problems.extend(entry["fit"]["reasons"])
    elif entry["fit"] and entry["fit"]["level"] == "cpu":
        level = "slow"
        problems.extend(entry["fit"]["reasons"])
    elif entry["fit"] and entry["fit"]["level"] == "partial":
        # Split between GPU and CPU: the configuration that was benchmarked at
        # 14 to 25 tokens/s. Worth knowing, not worth a warning banner.
        notes.extend(entry["fit"]["reasons"])
    if entry and not entry["commercial_ok"] and overview["commercial_only"]:
        level = "unsuitable" if level == "good" else level
        problems.append(f"{model_id}: {entry['license']['name']}. This deployment is set to commercial use, which needs a permissive licence.")
    alternatives = [] if level in ("good",) else local_fit.suggest_alternatives(exclude=model_id)
    return {"level": level, "problems": problems, "notes": notes, "alternatives": alternatives}


def _model_dict(m) -> Dict[str, Any]:
    return {
        "id": m.id,
        "size_gb": round(m.size_bytes / 1e9, 1) if m.size_bytes else None,
        "parameters": m.parameter_size,
        "quantization": m.quantization,
    }


@router.get("/inference/status")
async def inference_status(
    request: Request,
    x_rinti_admin: Optional[str] = Header(default=None),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    snapshot = routing.status_snapshot()
    try:
        require_admin(request, x_rinti_admin)
        can_configure = True
    except HTTPException:
        can_configure = False
    ollama = providers()["ollama"]
    health = ollama.health()
    cloud: List[Dict[str, Any]] = []
    for provider in cloud_providers().values():
        cloud.append({"id": provider.name, "label": provider.label, "configured": provider.is_configured()})

    overview = local_fit.overview()
    # A public, hosted backend doesn't tell anonymous visitors what server it runs on.
    reveal_hardware = can_configure or not overview["deployment"]["hosted"]
    return {
        **snapshot,
        "hardware": overview["hardware"] if reveal_hardware else None,
        "deployment": overview["deployment"],
        "recommendation": overview["recommendation"],
        "commercial_only": overview["commercial_only"],
        "assessment": _assessment(snapshot, health.reachable, overview),
        "local": {
            "models": overview["models"],
            "reachable": health.reachable,
            "detail": health.detail,
            "installed": [_model_dict(m) for m in health.models],
            "loaded": [
                {
                    "model": item.get("model"),
                    "size_gb": round((item.get("size_bytes") or 0) / 1e9, 1),
                    "gpu_gb": round((item.get("vram_bytes") or 0) / 1e9, 1),
                    "context": item.get("context"),
                }
                for item in health.loaded
            ],
            "general_ready": any(m.id == snapshot["local_model"] for m in health.models),
            "coding_ready": any(m.id == snapshot["coding_model"] for m in health.models),
        },
        "cloud": cloud,
        # Lets the UI explain why saving is disabled for this client.
        "can_configure": can_configure,
    }


@router.patch("/inference/config", dependencies=[Depends(verify_csrf_header), Depends(require_admin)])
async def update_inference_config(
    update: InferenceConfigUpdate, current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    installed = {m.id for m in providers()["ollama"].health().models}
    changes: Dict[str, Optional[str]] = {}

    if update.mode is not None:
        if update.mode not in routing.MODES:
            raise HTTPException(status_code=400, detail="Mode must be local, auto or cloud.")
        cloud = cloud_providers().get(routing.load_config().cloud_provider)
        cloud_ready = bool(cloud and cloud.is_configured())
        wants_fallback = update.cloud_fallback if update.cloud_fallback is not None else routing.load_config().cloud_fallback
        if (update.mode == "cloud" or (update.mode == "auto" and wants_fallback)) and not cloud_ready:
            raise HTTPException(status_code=400, detail="No cloud provider is configured on the server.")
        changes["inference_mode"] = update.mode

    if update.cloud_fallback is not None:
        cloud = cloud_providers().get(routing.load_config().cloud_provider)
        if update.cloud_fallback and not (cloud and cloud.is_configured()):
            raise HTTPException(status_code=400, detail="No cloud provider is configured on the server.")
        changes["cloud_fallback"] = "true" if update.cloud_fallback else "false"

    for field, key in (("local_model", "local_model"), ("coding_model", "coding_model")):
        value = getattr(update, field)
        if value is not None:
            if value not in installed:
                raise HTTPException(status_code=400, detail=f"'{value}' is not installed in Ollama.")
            changes[key] = value

    if update.cloud_model is not None:
        value = update.cloud_model.strip()
        if not value or len(value) > 120:
            raise HTTPException(status_code=400, detail="Enter a valid cloud model name.")
        changes["cloud_model"] = value

    for key, value in changes.items():
        db.set_app_config(key, value)
    routing.invalidate_config_cache()
    return {"status": "saved", "changed": sorted(changes)}
