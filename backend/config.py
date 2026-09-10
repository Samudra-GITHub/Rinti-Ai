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

settings = Settings()