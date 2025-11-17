"""
Database Schemas for Voice projects

Each Pydantic model represents a collection in MongoDB.
Model name lowercased is the collection name.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

class Voice(BaseModel):
    name: str = Field(..., description="Display name of the voice")
    description: Optional[str] = Field(None, description="Short description")
    language: str = Field(..., description="Language/locale, e.g., en-US")
    avatar_url: Optional[HttpUrl] = Field(None, description="Optional avatar image")
    samples: Optional[List[str]] = Field(default_factory=list, description="Sample file URLs")

class TTSJob(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice_id: Optional[str] = Field(None, description="Voice identifier (if using a custom voice)")
    language: str = Field("en", description="Language for TTS engine")
    format: str = Field("mp3", description="Audio format: mp3 or wav")
