import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", 8000))
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    
    db_path: str = os.getenv("DB_PATH", "rinti_memory.db")
    # Production persistence. When set, memory/db_backend.py routes every
    # connection to Postgres instead of the local SQLite file — Vercel
    # Functions have no durable local filesystem, so SQLite can't be the
    # production database there. Left unset, local dev behaviour (SQLite at
    # db_path) is completely unchanged.
    database_url: str = os.getenv("DATABASE_URL", "")

    def __init__(self, **data):
        super().__init__(**data)
        # Catch configuration errors early. In production (Vercel), DATABASE_URL
        # must be set — otherwise every request gets an ephemeral filesystem with
        # no database, and all writes fail. Local dev with DATABASE_URL also unset
        # is fine (uses SQLite). But if environment signals "production" with no
        # DATABASE_URL, that's a config error that should fail loudly at startup,
        # not silently with cryptic 500s on every request.
        if self.environment == "production" and not self.database_url:
            raise RuntimeError(
                "FATAL: environment=production but DATABASE_URL is not set. "
                "Vercel Functions have no durable filesystem — SQLite cannot be used for "
                "production. Set DATABASE_URL to a Postgres connection string "
                "(from Neon or another Marketplace provider)."
            )

    model_name: str = "openai/gpt-oss-120b"
    max_history_tokens: int = 2000
    # Upper bound on one chat reply. This is a safety ceiling, not a length
    # target: reply length is governed by the response policy in
    # core/personality.py. It is generous because reasoning models spend part
    # of this budget on hidden reasoning before the visible answer.
    max_response_tokens: int = int(os.getenv("MAX_RESPONSE_TOKENS", 4096))

    # ── Inference routing (see providers/ and core/inference.py) ──────────────
    # Legacy variables keep their names (OPENAI_API_KEY, OPENAI_BASE_URL); the
    # new inference group is namespaced with RINTI_. Defaults reproduce the
    # old behaviour exactly: cloud (Groq) only, no local model needed.
    #
    # RINTI_DEFAULT_PROVIDER: "groq" (cloud) or "ollama" (local).
    # RINTI_CLOUD_FALLBACK:   with ollama, allow falling back to the cloud when
    #                         the local model fails. false = strict local-only:
    #                         conversations never leave this machine.
    # Resulting mode: groq -> "cloud"; ollama+no fallback -> "local";
    #                 ollama+fallback -> "auto".
    default_provider: str = os.getenv("RINTI_DEFAULT_PROVIDER", "groq").strip().lower()
    cloud_fallback: bool = os.getenv("RINTI_CLOUD_FALLBACK", "false").strip().lower() in ("1", "true", "yes")
    # In "auto" mode, also send unusually demanding prompts to the cloud model.
    cloud_escalation: bool = os.getenv("RINTI_CLOUD_ESCALATION", "false").strip().lower() in ("1", "true", "yes")

    # Commercial deployment: only recommend models whose licence permits it
    # without further review (Apache-2.0, MIT). Off for personal use.
    commercial_use: bool = os.getenv("RINTI_COMMERCIAL_USE", "false").strip().lower() in ("1", "true", "yes")
    # Refuse (with an explanation, never a silent cloud switch) to load a local
    # model that clearly can't fit this machine's memory.
    hardware_check: bool = os.getenv("RINTI_HARDWARE_CHECK", "true").strip().lower() not in ("0", "false", "no")

    ollama_base_url: str = os.getenv("RINTI_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    # Local models. The coding and fast models fall back to the general one.
    default_model: str = os.getenv("RINTI_DEFAULT_MODEL", "qwen2.5:7b")
    coding_model: str = os.getenv("RINTI_CODING_MODEL", "")
    fast_model: str = os.getenv("RINTI_FAST_MODEL", "")
    # Empty means "use the legacy model_name" (see the end of this file), so an
    # existing deployment's MODEL_NAME keeps selecting the cloud model.
    cloud_model: str = os.getenv("RINTI_CLOUD_MODEL", "")

    # Context window requested from Ollama. Bigger windows cost VRAM (KV cache);
    # 8192 keeps a 7B Q4 model within 6 GB. Tune with RINTI_LOCAL_NUM_CTX.
    local_num_ctx: int = int(os.getenv("RINTI_LOCAL_NUM_CTX", 8192))
    cloud_context_tokens: int = int(os.getenv("RINTI_CLOUD_CONTEXT_TOKENS", 24000))
    local_max_response_tokens: int = int(os.getenv("RINTI_LOCAL_MAX_RESPONSE_TOKENS", 2048))
    ollama_keep_alive: str = os.getenv("RINTI_OLLAMA_KEEP_ALIVE", "10m")

    # Safety limits so one slow local generation can't take the machine down.
    local_max_concurrency: int = int(os.getenv("RINTI_LOCAL_MAX_CONCURRENCY", 1))
    cloud_max_concurrency: int = int(os.getenv("RINTI_CLOUD_MAX_CONCURRENCY", 8))
    queue_timeout_seconds: float = float(os.getenv("RINTI_QUEUE_TIMEOUT", 60))
    request_timeout_seconds: float = float(os.getenv("RINTI_REQUEST_TIMEOUT", 300))

    # Changing inference settings at runtime is allowed from this machine
    # (loopback) or with this token in the X-Rinti-Admin header. Unset on a
    # public deployment = remote changes are refused.
    admin_token: str = os.getenv("RINTI_ADMIN_TOKEN", "")

    # Optional extra OpenAI-compatible providers, as JSON, e.g.
    # [{"name":"openrouter","base_url":"https://openrouter.ai/api/v1",
    #   "api_key_env":"OPENROUTER_API_KEY","model":"meta-llama/llama-3.1-70b-instruct"}]
    # The key is read from the named environment variable, never from this JSON.
    extra_providers: str = os.getenv("RINTI_EXTRA_PROVIDERS", "")

    # Per-user daily caps. The Groq/Tavily API keys are one shared, server-side
    # account for the whole app — there's no way to give each user an
    # independently-metered provider quota without each of them bringing their
    # own key. This is the fair-share alternative: the app itself tracks and
    # caps each authenticated user's usage, so one heavy user hitting the
    # account-wide ceiling doesn't happen from a single person alone, and one
    # user being at their limit never affects any other user's own count.
    max_chat_messages_per_day: int = int(os.getenv("MAX_CHAT_MESSAGES_PER_DAY", 40))
    max_research_queries_per_day: int = int(os.getenv("MAX_RESEARCH_QUERIES_PER_DAY", 8))

    # CORS allowlist. The browser only ever talks to the Next.js origin
    # (same-origin proxy architecture — see app/api/[...path]/route.ts), so
    # this only matters as defense-in-depth against a browser hitting this
    # backend directly. Comma-separated in production, e.g.
    # "https://rinti-ai.vercel.app,https://your-custom-domain.com".
    allowed_origins: str = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

settings = Settings()
if not settings.cloud_model:
    settings.cloud_model = settings.model_name
