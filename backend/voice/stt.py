import io
from openai import OpenAI
from config import settings

client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url if settings.openai_base_url else None
)

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    buffer = io.BytesIO(audio_bytes)
    buffer.name = filename
    
    transcript = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",  # Groq's high-speed Whisper model
        file=buffer
    )
    return transcript.text