from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import memory.database as db
from auth.dependencies import get_current_user, verify_csrf_header

router = APIRouter()

class SettingsResponse(BaseModel):
    tts_enabled: bool
    wake_word_enabled: bool
    memory_enabled: bool
    voice_id: str

class SettingsUpdateRequest(BaseModel):
    tts_enabled: Optional[bool] = None
    wake_word_enabled: Optional[bool] = None
    memory_enabled: Optional[bool] = None
    voice_id: Optional[str] = None

class VoiceOption(BaseModel):
    id: str
    name: str
    preview_url: Optional[str]

class ModelAvailability(BaseModel):
    id: str
    provider: str
    available: bool

@router.get("/settings", response_model=SettingsResponse)
async def get_settings_endpoint(current_user: dict = Depends(get_current_user)):
    try:
        data = db.get_settings()
        return SettingsResponse(
            tts_enabled=bool(data["tts_enabled"]),
            wake_word_enabled=bool(data["wake_word_enabled"]),
            memory_enabled=bool(data["memory_enabled"]),
            voice_id=data["voice_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/settings",
    response_model=SettingsResponse,
    dependencies=[Depends(verify_csrf_header)],
)
async def update_settings_endpoint(request: SettingsUpdateRequest, current_user: dict = Depends(get_current_user)):
    try:
        updates = {k: v for k, v in request.model_dump().items() if v is not None}
        updated_data = db.update_settings(updates)
        return SettingsResponse(
            tts_enabled=bool(updated_data["tts_enabled"]),
            wake_word_enabled=bool(updated_data["wake_word_enabled"]),
            memory_enabled=bool(updated_data["memory_enabled"]),
            voice_id=updated_data["voice_id"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voices", response_model=List[VoiceOption])
async def get_voices_endpoint(current_user: dict = Depends(get_current_user)):
    return [
        {"id": "alloy", "name": "Rinti Natural (Alloy)", "preview_url": None},
        {"id": "nova", "name": "Rinti Warm (Nova)", "preview_url": None},
        {"id": "shimmer", "name": "Rinti Bright (Shimmer)", "preview_url": None},
        {"id": "echo", "name": "Rinti Deep (Echo)", "preview_url": None},
        {"id": "fable", "name": "Rinti Expressive (Fable)", "preview_url": None},
        {"id": "onyx", "name": "Rinti Calm (Onyx)", "preview_url": None},
    ]

@router.get("/models", response_model=List[ModelAvailability])
async def get_models_endpoint(current_user: dict = Depends(get_current_user)):
    """Models the user may pick. Every entry has been verified: local models come
    from what Ollama reports as installed, the cloud model only appears when a
    key is configured and the policy allows cloud use. Never exposes keys or URLs."""
    from core.routing import load_config
    from providers.registry import cloud_providers, providers

    cfg = load_config()
    models: List[dict] = []

    if cfg.mode != "cloud":  # cloud mode never touches Ollama (it can't exist on a hosted backend)
        local_health = providers()["ollama"].health()
        if local_health.reachable:
            models.extend({"id": m.id, "provider": "ollama", "available": True} for m in local_health.models)

    cloud = cloud_providers().get(cfg.cloud_provider)
    # Same rule as plan_route: the cloud is offered in Cloud mode, or in Auto only when its fallback is on.
    cloud_allowed = cfg.mode == "cloud" or (cfg.mode == "auto" and cfg.cloud_fallback)
    if cloud_allowed and cloud and cloud.is_configured():
        models.append({"id": cfg.cloud_model, "provider": cloud.name, "available": True})

    # "Auto" lets the router choose (shown first and used by default).
    if models:
        models.insert(0, {"id": "auto", "provider": "router", "available": True})
    return models
