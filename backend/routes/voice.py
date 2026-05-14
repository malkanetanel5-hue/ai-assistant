import os
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from openai import OpenAI

router = APIRouter(prefix="/voice", tags=["voice"])

# Whisper accepts these container formats
_ALLOWED_TYPES = {
    "audio/webm", "audio/ogg", "audio/wav", "audio/mp4",
    "audio/mpeg", "audio/mp3", "audio/flac", "audio/x-m4a",
}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    Accept a browser MediaRecorder blob (webm/opus is the default) and return
    the Whisper transcript.  The frontend sends the file as multipart/form-data
    with the field name 'audio'.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    content_type = audio.content_type or "audio/webm"
    if not any(content_type.startswith(t.split("/")[0]) for t in _ALLOWED_TYPES):
        raise HTTPException(status_code=415, detail=f"Unsupported audio type: {content_type}")

    # Map MIME → file extension so Whisper's server knows the container
    ext_map = {
        "audio/webm": ".webm", "audio/ogg": ".ogg",
        "audio/wav": ".wav",  "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
        "audio/flac": ".flac", "audio/x-m4a": ".m4a",
    }
    suffix = ext_map.get(content_type, ".webm")

    data = await audio.read()
    if len(data) < 1000:
        raise HTTPException(status_code=400, detail="Audio too short or empty")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
            )
        return {"transcript": str(transcript).strip()}
    finally:
        os.unlink(tmp_path)
