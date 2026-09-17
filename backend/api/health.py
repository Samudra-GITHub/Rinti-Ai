from fastapi import APIRouter

from config import settings
from memory import db_backend

router = APIRouter()


def _check_groq() -> dict:
    """Lightweight reachability probe. Uses the models-list endpoint, which
    is metadata-only and does not consume completion token quota — a real
    chat/research call would burn from the same daily Groq TPD budget the
    app itself depends on, which a diagnostics endpoint must never do."""
    if not settings.openai_api_key:
        return {"configured": False, "reachable": False}
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url, timeout=5.0)
        client.models.list()
        return {"configured": True, "reachable": True}
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        return {"configured": True, "reachable": False, "error": str(exc)[:200]}


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
        "groq": _check_groq(),
        "tavily": _check_tavily(),
    }
