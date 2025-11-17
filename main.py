import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import create_document, get_documents, db
from schemas import Voice as VoiceSchema, TTSJob as TTSJobSchema

# Constants
OUTPUT_DIR = os.path.join(os.getcwd(), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="AI Voice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated audio files
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")


class TTSResponse(BaseModel):
    id: str
    text: str
    voice_id: Optional[str]
    language: str
    format: str
    status: str
    audio_url: Optional[str] = None
    created_at: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "AI Voice Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -----------------------------
# Voices
# -----------------------------
DEFAULT_VOICES = [
    {
        "name": "Nova",
        "description": "Warm, clear American English voice",
        "language": "en",
        "avatar_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=400&auto=format&fit=crop"
    },
    {
        "name": "Aria",
        "description": "Natural British English voice",
        "language": "en-GB",
        "avatar_url": "https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?q=80&w=400&auto=format&fit=crop"
    },
    {
        "name": "Sora",
        "description": "Smooth Japanese voice",
        "language": "ja",
        "avatar_url": "https://images.unsplash.com/photo-1545996124-0501ebae84d0?q=80&w=400&auto=format&fit=crop"
    },
    {
        "name": "Mateo",
        "description": "Crisp Spanish voice",
        "language": "es",
        "avatar_url": "https://images.unsplash.com/photo-1527980965255-d3b416303d12?q=80&w=400&auto=format&fit=crop"
    },
]


@app.get("/api/voices", response_model=List[VoiceSchema])
def list_voices():
    try:
        voices = []
        if db is not None:
            voices = get_documents("voice")
            # Convert ObjectId to string if present
            for v in voices:
                v.pop("_id", None)
        if not voices:
            return DEFAULT_VOICES
        return voices
    except Exception:
        return DEFAULT_VOICES


@app.post("/api/voices", response_model=str)
def create_voice(voice: VoiceSchema):
    try:
        vid = create_document("voice", voice)
        return vid
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# TTS
# -----------------------------
@app.post("/api/tts", response_model=TTSResponse)
def synthesize_speech(job: TTSJobSchema):
    from gtts import gTTS

    text = job.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # File name
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    ext = "mp3" if (job.format or "mp3").lower() == "mp3" else "mp3"
    fname = f"tts_{ts}.{ext}"
    fpath = os.path.join(OUTPUT_DIR, fname)

    # Generate using gTTS
    try:
        tts = gTTS(text=text, lang=(job.language or "en"))
        tts.save(fpath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

    audio_url = f"/generated/{fname}"

    # Persist job
    doc = {
        "text": text,
        "voice_id": job.voice_id,
        "language": job.language or "en",
        "format": job.format or "mp3",
        "status": "completed",
        "audio_url": audio_url,
    }
    try:
        job_id = create_document("ttsjob", doc)
    except Exception:
        job_id = ""

    return TTSResponse(
        id=job_id,
        text=text,
        voice_id=job.voice_id,
        language=job.language or "en",
        format=job.format or "mp3",
        status="completed",
        audio_url=audio_url,
        created_at=datetime.utcnow().isoformat()
    )


@app.get("/api/jobs")
def list_jobs(limit: int = 20):
    try:
        jobs = get_documents("ttsjob", limit=limit)
        # serialize ObjectId
        for j in jobs:
            if "_id" in j:
                j["id"] = str(j.pop("_id"))
        return jobs
    except Exception:
        return []


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
