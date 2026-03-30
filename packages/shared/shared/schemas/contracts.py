"""JSON output contracts for AI planning stages.

Each model defines the *exact* JSON shape that the corresponding AI call must
produce.  The :func:`shared.providers.validation.generate_validated` helper
validates every response against these contracts and retries on mismatch.

Validation philosophy:
  - min_length >= 5 for descriptive fields to block placeholder "..." answers
  - Literal types for enumerated values (camera, framing, transitions)
  - Cross-field validators where consistency matters
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ── Shared enums ──────────────────────────────────────

CameraFraming = Literal[
    "extreme_wide", "wide", "medium_wide", "medium",
    "medium_close_up", "close_up", "extreme_close_up",
    "overhead", "low_angle", "birds_eye",
]

CameraMotion = Literal[
    "static", "slow_pan_left", "slow_pan_right", "pan_left", "pan_right",
    "tilt_up", "tilt_down", "dolly_in", "dolly_out",
    "tracking_left", "tracking_right", "tracking_forward",
    "crane_up", "crane_down", "handheld", "orbit_left", "orbit_right",
    "zoom_in", "zoom_out", "push_in",
]

ShotType = Literal[
    "establishing", "insert", "reaction", "action", "cutaway",
    "over_the_shoulder", "point_of_view", "montage_element",
    "detail", "reveal", "transition", "title_card",
]

Transition = Literal[
    "cut", "fade_in", "fade_out", "dissolve_in", "dissolve_out",
    "wipe_in", "wipe_out", "cross_dissolve", "none",
]

AssetStrategy = Literal[
    "image_to_video", "direct_video", "still_image", "mixed",
]

FrameRole = Literal["start", "middle", "end"]


# ── 1. Script Plan ───────────────────────────────────


class ScriptSection(BaseModel):
    """One logical section of the script plan."""

    title: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5, description="What this section achieves")
    narration: str = Field(..., min_length=5, description="Exact spoken narration text")
    visual_notes: str = Field(
        ..., min_length=5,
        description="Concrete visual direction: what appears on screen",
    )
    duration_sec: float = Field(ge=2, le=300, default=10)


class ScriptPlanOutput(BaseModel):
    """Full structured script plan produced by AI from user inputs."""

    title: str = Field(..., min_length=2)
    summary: str = Field(..., min_length=10)
    hook: str = Field(..., min_length=5, description="First 3-second attention grabber")
    narrative_flow: list[str] = Field(..., min_length=2)
    sections: list[ScriptSection] = Field(..., min_length=2)
    ending_cta: str = Field(..., min_length=5)
    narration_draft: str = Field(..., min_length=20)
    estimated_duration_sec: float = Field(ge=5, le=3600)

    @model_validator(mode="after")
    def check_section_durations(self):
        total = sum(s.duration_sec for s in self.sections)
        target = self.estimated_duration_sec
        if target > 0 and abs(total - target) / target > 0.3:
            raise ValueError(
                f"Section durations sum ({total:.0f}s) deviates >30% "
                f"from estimated_duration_sec ({target:.0f}s)"
            )
        return self


# ── 2. Scene Breakdown ───────────────────────────────


class SceneBreakdownItem(BaseModel):
    """One scene produced by the scene planner."""

    scene_index: int = Field(ge=0)
    title: str = Field(..., min_length=2)
    purpose: str = Field(..., min_length=5, description="Narrative function of this scene")
    summary: str = Field(..., min_length=10)
    narration_text: str = Field(..., min_length=5, description="Exact voiceover for this scene")
    setting: str = Field(..., min_length=3, description="Location/environment in English")
    mood: str = Field(..., min_length=2, description="One-word or short-phrase mood")
    emotional_tone: str = Field(
        ..., min_length=5,
        description="Detailed emotional direction for visuals and music",
    )
    visual_intent: str = Field(
        ..., min_length=15,
        description="What the viewer SEES — in English, concrete enough for image AI",
    )
    transition_hint: str = Field(default="cut")
    estimated_duration_sec: float = Field(ge=2, le=300)


class SceneBreakdownOutput(BaseModel):
    """Full scene breakdown from a ScriptVersion."""

    scenes: list[SceneBreakdownItem] = Field(..., min_length=1)
    total_duration_sec: float = Field(ge=1)

    @model_validator(mode="after")
    def check_duration_sum(self):
        actual = sum(s.estimated_duration_sec for s in self.scenes)
        if abs(actual - self.total_duration_sec) > 5:
            raise ValueError(
                f"Scene duration sum ({actual:.0f}s) doesn't match "
                f"total_duration_sec ({self.total_duration_sec:.0f}s)"
            )
        return self


class SingleSceneOutput(BaseModel):
    """Regenerated single scene."""

    title: str = Field(..., min_length=2)
    purpose: str = Field(..., min_length=5)
    summary: str = Field(..., min_length=10)
    narration_text: str = Field(..., min_length=5)
    setting: str = Field(..., min_length=3)
    mood: str = Field(..., min_length=2)
    emotional_tone: str = Field(..., min_length=5)
    visual_intent: str = Field(..., min_length=15)
    transition_hint: str = Field(default="cut")
    estimated_duration_sec: float = Field(ge=2, le=300)


# ── 3. Shot Breakdown ────────────────────────────────


class ShotBreakdownItem(BaseModel):
    """One shot within a scene, produced by the shot planner."""

    shot_index: int = Field(ge=0)
    purpose: str = Field(..., min_length=5)
    duration_sec: float = Field(ge=1.5, le=15)
    shot_type: str = Field(..., min_length=3)
    camera_framing: str = Field(..., min_length=3)
    camera_motion: str = Field(default="static", min_length=3)
    subject: str = Field(
        ..., min_length=5,
        description="Main visual subject in English, specific enough for image AI",
    )
    environment: str = Field(
        ..., min_length=5,
        description="Background/environment details in English",
    )
    emotion: str = Field(..., min_length=3)
    narration_segment: str = ""
    transition_in: str = Field(default="cut")
    transition_out: str = Field(default="cut")
    asset_strategy: str = Field(default="image_to_video")
    description: str = Field(
        ..., min_length=30,
        description="Standalone visual prompt: subject + action + environment + lighting + mood",
    )


class ShotBreakdownOutput(BaseModel):
    """All shots for a single scene."""

    shots: list[ShotBreakdownItem] = Field(..., min_length=1)
    total_duration_sec: float = Field(ge=1)

    @model_validator(mode="after")
    def check_duration_sum(self):
        actual = sum(s.duration_sec for s in self.shots)
        if abs(actual - self.total_duration_sec) > 3:
            raise ValueError(
                f"Shot duration sum ({actual:.1f}s) doesn't match "
                f"total_duration_sec ({self.total_duration_sec:.1f}s)"
            )
        return self


class SingleShotOutput(BaseModel):
    """Regenerated single shot."""

    purpose: str = Field(..., min_length=5)
    duration_sec: float = Field(ge=1.5, le=15)
    shot_type: str = Field(..., min_length=3)
    camera_framing: str = Field(..., min_length=3)
    camera_motion: str = Field(default="static", min_length=3)
    subject: str = Field(..., min_length=5)
    environment: str = Field(..., min_length=5)
    emotion: str = Field(..., min_length=3)
    narration_segment: str = ""
    transition_in: str = Field(default="cut")
    transition_out: str = Field(default="cut")
    asset_strategy: str = Field(default="image_to_video")
    description: str = Field(..., min_length=30)


# ── 4. Frame Spec Breakdown ──────────────────────────


class FrameSpecItem(BaseModel):
    """One frame spec (start / middle / end) within a shot."""

    frame_role: str = Field(..., pattern=r"^(start|middle|end)$")
    composition: str = Field(
        ..., min_length=10,
        description="Rule-of-thirds, leading lines, depth layers, framing technique",
    )
    subject_position: str = Field(
        ..., min_length=5,
        description="Grid position e.g. 'right-third intersection, upper body filling center-right 40%'",
    )
    camera_angle: str = Field(
        ..., min_length=3,
        description="e.g. 'eye-level', 'low-angle 15°', 'dutch angle 10°'",
    )
    lens_feel: str = Field(
        ..., min_length=5,
        description="Focal length + DOF e.g. '85mm portrait, shallow DOF f/1.8'",
    )
    lighting: str = Field(
        ..., min_length=10,
        description="Key/fill/rim setup e.g. 'warm key from camera-left 45°, soft fill from right, cool rim behind'",
    )
    mood: str = Field(..., min_length=3)
    action_pose: str = Field(
        ..., min_length=5,
        description="Specific pose/gesture/expression, not abstract feelings",
    )
    background_description: str = Field(
        ..., min_length=10,
        description="Detailed background in English for generation AI",
    )
    continuity_notes: str = Field(
        default="",
        description="What must stay consistent with adjacent frames",
    )
    forbidden_elements: str = Field(
        default="",
        description="Elements that must NOT appear to avoid generation artifacts",
    )


class FrameSpecOutput(BaseModel):
    """All frame specs for a single shot (2–3 frames: start, [middle], end)."""

    frames: list[FrameSpecItem] = Field(..., min_length=2, max_length=4)

    @model_validator(mode="after")
    def check_start_end(self):
        roles = {f.frame_role for f in self.frames}
        if "start" not in roles:
            raise ValueError("Must include a 'start' frame")
        if "end" not in roles:
            raise ValueError("Must include an 'end' frame")
        return self


class SingleFrameSpecOutput(BaseModel):
    """Regenerated single frame spec."""

    composition: str = Field(..., min_length=10)
    subject_position: str = Field(..., min_length=5)
    camera_angle: str = Field(..., min_length=3)
    lens_feel: str = Field(..., min_length=5)
    lighting: str = Field(..., min_length=10)
    mood: str = Field(..., min_length=3)
    action_pose: str = Field(..., min_length=5)
    background_description: str = Field(..., min_length=10)
    continuity_notes: str = ""
    forbidden_elements: str = ""


# ── 5. Legacy: Script Structuring (full hierarchy) ───


class ScriptGenerateOutput(BaseModel):
    title: str = Field(..., min_length=1)
    raw_text: str = Field(..., min_length=10)
    summary: str = ""
    estimated_duration_sec: float = Field(ge=5, le=3600, default=60)


class FramePlan(BaseModel):
    visual_prompt: str = Field(..., min_length=5)
    negative_prompt: str = ""
    dialogue: str = ""
    dialogue_character: str = ""
    duration_ms: int = Field(ge=500, le=30000, default=3000)
    transition_type: str = Field(default="cut")


class ShotPlan(BaseModel):
    shot_type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    camera_movement: str = Field(default="static")
    duration_sec: float = Field(ge=0.5, le=120, default=3)
    frames: list[FramePlan] = Field(..., min_length=1)


class ScenePlan(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    setting: str = ""
    mood: str = ""
    duration_estimate_sec: float = Field(ge=1, le=600, default=15)
    shots: list[ShotPlan] = Field(..., min_length=1)


class ScriptStructureOutput(BaseModel):
    scenes: list[ScenePlan] = Field(..., min_length=1)


class ScenePlanOutput(BaseModel):
    scene_title: str
    shots: list[ShotPlan] = Field(..., min_length=1)


class ShotPlanOutput(BaseModel):
    shot_description: str
    frames: list[FramePlan] = Field(..., min_length=1)


class FramePromptOutput(BaseModel):
    visual_prompt: str = Field(..., min_length=10)
    negative_prompt: str = ""
    style_notes: str = ""
