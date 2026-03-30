from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from shared.schemas.enums import ProjectStatus


class SubtitleStyleSettings(BaseModel):
    """Default subtitle style stored in ProjectSettings."""
    max_chars_per_line: int = 35
    max_lines: int = 2
    line_break_strategy: str = "word"
    gap_ms: int = 100
    min_segment_ms: int = 500
    max_segment_ms: int = 6000


class ProjectSettings(BaseModel):
    """Value object stored as JSON in Project.settings."""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    aspect_ratio: str = "16:9"
    output_format: str = "mp4"
    default_frame_duration_ms: int = 3000
    default_language: str = "ko"
    default_tts_provider: str = "elevenlabs"
    default_image_model: str = "fal"
    default_video_model: str = "runway"
    subtitle_style: SubtitleStyleSettings = SubtitleStyleSettings()


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    active_style_preset_id: UUID | None = None
    settings: ProjectSettings | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None
    active_style_preset_id: UUID | None = None
    settings: ProjectSettings | None = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    title: str
    description: str | None
    status: str
    active_style_preset_id: UUID | None
    settings: dict | None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int
