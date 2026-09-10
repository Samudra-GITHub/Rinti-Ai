from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from voice.stt import transcribe_audio
from voice.tts import synthesize_speech
import memory.database as db

router = APIRouter()

class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

@router.post("/voice/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio payload")
        transcript = transcribe_audio(audio_bytes, filename=file.filename or "recording.wav")
        return {"text": transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/voice/synthesize")
async def synthesize_endpoint(request: SynthesizeRequest):
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        voice_id = request.voice_id
        if not voice_id:
            current_settings = db.get_settings()
            voice_id = current_settings.get("voice_id", "alloy")
            
        audio_content = synthesize_speech(request.text, voice_id=voice_id)
        return Response(content=audio_content, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")