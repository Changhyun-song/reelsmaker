from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubtitleSegment(BaseModel):
    """Single subtitle cue."""
    index: int
    start_ms: int
    end_ms: int
    text: str
    shot_id: str | None = None
    speaker: str | None = None


class SubtitleStyleConfig(BaseModel):
    max_chars_per_line: int = Field(default=35, ge=10, le=80)
    max_lines: int = Field(default=2, ge=1, le=4)
    line_break_strategy: str = Field(default="word")
    gap_ms: int = Field(default=100, ge=0, le=2000)
    min_segment_ms: int = Field(default=500, ge=100, le=3000)
    max_segment_ms: int = Field(default=6000, ge=1000, le=30000)


class SubtitleGenerateRequest(BaseModel):
    script_version_id: UUID
    style: SubtitleStyleConfig | None = None
    format: str = Field(default="srt")
    language: str = Field(default="ko")


class SubtitleTrackResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    script_version_id: UUID | None
    language: str
    format: str
    timing_source: str
    segments: list[SubtitleSegment] | None = None
    style_settings: dict | None
    content: str | None
    total_segments: int | None
    total_duration_ms: int | None
    asset_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class SubtitleTrackListResponse(BaseModel):
    tracks: list[SubtitleTrackResponse]
    total: int
