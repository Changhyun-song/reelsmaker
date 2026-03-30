"""Timeline data structures for render-ready composition."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TransitionSpec(BaseModel):
    type: str = "cut"  # "cut" | "xfade" | "fade_in" | "fade_out" | "custom_dip"
    duration_ms: int = 0
    params: dict = Field(default_factory=dict)
    ffmpeg_xfade_name: str | None = None


class ImageMotionSpec(BaseModel):
    """Ken Burns-style motion for still-image shots."""
    effect: str = "ken_burns"
    zoom_start: float = 1.0
    zoom_end: float = 1.15
    pan_direction: str = "left_to_right"
    easing: str = "linear"  # "linear" | "ease_in" | "ease_out" | "ease_in_out"
    preset_name: str | None = None
    params: dict = Field(default_factory=dict)


class VideoSegment(BaseModel):
    """One shot's visual segment on the timeline."""
    index: int
    shot_id: str
    scene_id: str
    start_ms: int
    end_ms: int
    duration_ms: int

    asset_type: str  # "video" | "image" | "missing"
    asset_id: str | None = None
    storage_key: str | None = None

    transition_in: TransitionSpec = TransitionSpec()
    transition_out: TransitionSpec = TransitionSpec()

    image_motion: ImageMotionSpec | None = None

    pacing_zone: str = "body"  # "hook" | "body" | "climax" | "outro"
    shot_metadata: dict = Field(default_factory=dict)


class AudioSegment(BaseModel):
    """One shot's narration audio segment on the timeline."""
    index: int
    shot_id: str
    start_ms: int
    end_ms: int
    duration_ms: int

    asset_id: str | None = None
    storage_key: str | None = None
    voice_track_id: str | None = None
    voice_id: str | None = None
    status: str = "missing"


class PauseSegment(BaseModel):
    """A silence/beat/gap inserted between scenes or at beats."""
    index: int
    start_ms: int
    end_ms: int
    duration_ms: int
    pause_type: str = "scene_gap"  # "scene_gap" | "beat" | "hook_pause" | "breath"
    visual: str = "hold_last"  # "hold_last" | "black" | "fade_black"
    after_shot_id: str | None = None


class TimelineData(BaseModel):
    """Complete render-ready timeline structure stored in Timeline.segments."""
    version: int = 2
    format_profile: str = "shorts"
    total_duration_ms: int = 0
    video_segments: list[VideoSegment] = Field(default_factory=list)
    audio_segments: list[AudioSegment] = Field(default_factory=list)
    pause_segments: list[PauseSegment] = Field(default_factory=list)
    subtitle_track_id: str | None = None
    bgm_asset_id: str | None = None

    intro_fade_in_ms: int = 0
    outro_fade_out_ms: int = 0

    warnings: list[str] = Field(default_factory=list)

    output_settings: dict = Field(default_factory=lambda: {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "format": "mp4",
        "codec": "h264",
    })


class TimelineResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    script_version_id: UUID
    total_duration_ms: int | None
    segments: TimelineData | None = None
    bgm_asset_id: UUID | None
    subtitle_track_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class TimelineListResponse(BaseModel):
    timelines: list[TimelineResponse]
    total: int


class TimelineSummary(BaseModel):
    """Lightweight summary for UI display."""
    id: str
    status: str
    total_duration_ms: int
    total_shots: int
    shots_with_video: int
    shots_with_image_only: int
    shots_missing_visual: int
    shots_with_audio: int
    shots_missing_audio: int
    has_subtitle: bool
    has_bgm: bool
    warnings: list[str]
    format_profile: str = "shorts"
    pause_count: int = 0
    intro_fade_in_ms: int = 0
    outro_fade_out_ms: int = 0
    created_at: str
