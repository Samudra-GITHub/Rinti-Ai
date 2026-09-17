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
    model_name: str = "openai/gpt-oss-120b"
    max_history_tokens: int = 2000

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