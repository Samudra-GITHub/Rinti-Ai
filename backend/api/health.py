from fastapi import APIRouter

from config import settings
from memory import db_backend

router = APIRouter()


def _check_inference() -> dict:
    """Provider reachability. Cloud providers are only contacted when the current
    mode allows cloud use, so strict local-only mode never touches them."""
    from core.routing import load_config
    from providers.registry import cloud_providers, providers

    cfg = load_config()
    result = {"mode": cfg.mode}
    if cfg.mode == "cloud":
        # Cloud mode never uses Ollama, so don't probe it (and reveal nothing about it).
        result["local"] = {"checked": False}
    else:
        local = providers()["ollama"].health()
        result["local"] = {
            "checked": True,
            "reachable": local.reachable,
            "default_model_ready": any(m.id == cfg.local_model for m in local.models),
        }
    cloud = cloud_providers().get(cfg.cloud_provider)
    if cloud is not None:
        if cfg.mode == "local":
            result["cloud"] = {"configured": cloud.is_configured(), "checked": False}
        else:
            health = cloud.health() if cloud.is_configured() else None
            result["cloud"] = {
                "configured": cloud.is_configured(),
                "checked": True,
                "reachable": bool(health and health.reachable),
            }
    return result


def _check_tavily() -> dict:
    """Reports configuration only, not live reachability — Tavily's search
    endpoint consumes a billed credit per call, so a diagnostics endpoint
    that might be polled repeatedly must not spend one on every hit."""
    from research.config import tavily_api_key

    return {"configured": bool(tavily_api_key())}


def _check_schema() -> bool:
    try:
        conn = db_backend.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users LIMIT 1")
        cursor.fetchall()
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


@router.get("/health")
async def health_check():
    db_status = db_backend.health_check()
    return {
        "status": "ok" if db_status["connected"] else "degraded",
        "assistant": "Rinti",
        "version": "0.2.0",
        "environment": settings.environment,
        "database": db_status,
        "schema_initialized": _check_schema(),
        "inference": _check_inference(),
        "tavily": _check_tavily(),
    }
