from enum import Enum


# ── Project ───────────────────────────────────────────

class ProjectStatus(str, Enum):
    draft = "draft"
    scripting = "scripting"
    generating = "generating"
    composing = "composing"
    rendered = "rendered"
    archived = "archived"


# ── ScriptVersion ─────────────────────────────────────

class ScriptVersionStatus(str, Enum):
    draft = "draft"
    structuring = "structuring"
    structured = "structured"
    approved = "approved"


# ── Scene ─────────────────────────────────────────────

class SceneStatus(str, Enum):
    drafted = "drafted"
    approved = "approved"
    needs_revision = "needs_revision"


# ── Shot ──────────────────────────────────────────────

class ShotStatus(str, Enum):
    drafted = "drafted"
    approved = "approved"
    needs_revision = "needs_revision"
    generating_video = "generating_video"
    video_ready = "video_ready"
    video_failed = "video_failed"


# ── FrameSpec ────────────────────────────────────────

class ContentStatus(str, Enum):
    """Shared status for frame planning stages."""
    draft = "draft"
    ready = "ready"


class FrameSpecStatus(str, Enum):
    drafted = "drafted"
    approved = "approved"
    needs_revision = "needs_revision"
    prompts_ready = "prompts_ready"
    generating = "generating"
    generated = "generated"
    failed = "failed"


# ── Asset ─────────────────────────────────────────────

class AssetType(str, Enum):
    image = "image"
    video = "video"
    audio_tts = "audio_tts"
    audio_bgm = "audio_bgm"
    subtitle = "subtitle"
    render = "render"
    json = "json"
    project_file = "project_file"


class AssetStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    failed = "failed"


# ── VoiceTrack / SubtitleTrack ────────────────────────

class TrackStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    failed = "failed"


class SubtitleFormat(str, Enum):
    srt = "srt"
    ass = "ass"
    vtt = "vtt"


# ── Timeline ─────────────────────────────────────────

class TimelineStatus(str, Enum):
    draft = "draft"
    composing = "composing"
    composed = "composed"
    failed = "failed"


# ── RenderJob ─────────────────────────────────────────

class RenderJobStatus(str, Enum):
    queued = "queued"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


# ── ProviderRun ───────────────────────────────────────

class ProviderRunStatus(str, Enum):
    started = "started"
    completed = "completed"
    failed = "failed"


class ProviderName(str, Enum):
    openai = "openai"
    claude = "claude"
    fal = "fal"
    runway = "runway"
    elevenlabs = "elevenlabs"


# ── Job Queue ─────────────────────────────────────────

class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JobType(str, Enum):
    demo = "demo"
    script_generate = "script_generate"
    script_structure = "script_structure"
    scene_plan = "scene_plan"
    scene_regenerate = "scene_regenerate"
    shot_plan = "shot_plan"
    shot_regenerate = "shot_regenerate"
    frame_plan = "frame_plan"
    frame_regenerate = "frame_regenerate"
    image_generate = "image_generate"
    video_generate = "video_generate"
    tts_generate = "tts_generate"
    subtitle_generate = "subtitle_generate"
    timeline_compose = "timeline_compose"
    render_final = "render_final"
