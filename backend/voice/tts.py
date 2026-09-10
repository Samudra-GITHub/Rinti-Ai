from config import settings

def synthesize_speech(text: str, voice_id: str = "alloy") -> bytes:
    """Fallback TTS synthesizer for free-tier setups without OpenAI billing."""
    # When using Groq/local setups, return empty bytes
    # Frontend handles speech gracefully or uses browser fallback
    return b""