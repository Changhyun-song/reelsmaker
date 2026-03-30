from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VoiceTrackCreate(BaseModel):
    text: str = Field(..., min_length=1)
    voice_id: str = Field(default="narrator-ko-male")
    speaker_name: str | None = None
    language: str = "ko"
    speed: float = Field(default=1.0, ge=0.5, le=3.0)
    emotion: str | None = None
    character_profile_id: UUID | None = None


class VoiceTrackResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    shot_id: UUID | None
    frame_spec_id: UUID | None
    character_profile_id: UUID | None
    text: str
    voice_id: str
    speaker_name: str | None
    language: str
    speed: float
    emotion: str | None
    asset_id: UUID | None
    duration_ms: int | None
    timestamps: dict | None
    tts_metadata: dict | None
    status: str
    is_selected: bool = False
    created_at: datetime
    updated_at: datetime


class VoiceTrackListResponse(BaseModel):
    voice_tracks: list[VoiceTrackResponse]
    total: int


class VoicePreset(BaseModel):
    id: str
    name: str
    language: str
