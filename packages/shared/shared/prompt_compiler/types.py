"""Pure data types for Prompt Compiler — no DB or ORM dependency.

These Pydantic models serve as the compiler's interface. The API layer
converts ORM objects into these types before calling compiler functions.
"""

from pydantic import BaseModel, Field


class StyleContext(BaseModel):
    """Extracted from StylePreset."""
    name: str = ""
    style_keywords: str = ""
    color_palette: str = ""
    rendering_style: str = ""
    camera_language: str = ""
    lighting_rules: str = ""
    negative_rules: str = ""
    prompt_prefix: str = ""
    prompt_suffix: str = ""
    negative_prompt: str = ""
    # Anchor fields
    style_anchor: str = ""
    color_temperature: str = ""
    texture_quality: str = ""
    depth_style: str = ""
    environment_rules: str = ""


class CharacterContext(BaseModel):
    """Extracted from CharacterProfile."""
    name: str = ""
    role: str = ""
    appearance: str = ""
    outfit: str = ""
    age_impression: str = ""
    facial_traits: str = ""
    pose_rules: str = ""
    forbidden_changes: str = ""
    visual_prompt: str = ""
    # Extended identity fields
    body_type: str = ""
    hair_description: str = ""
    skin_tone: str = ""
    signature_props: str = ""
    forbidden_drift: str = ""


class ContinuityContext(BaseModel):
    """Extracted from ContinuityProfile — project-level consistency rules."""
    enabled: bool = True
    color_palette_lock: str = ""
    lighting_anchor: str = ""
    color_temperature_range: str = ""
    environment_consistency: str = ""
    style_anchor_summary: str = ""
    character_lock_notes: str = ""
    forbidden_global_drift: str = ""
    temporal_rules: str = ""


class SceneContext(BaseModel):
    """Extracted from Scene."""
    title: str = ""
    setting: str = ""
    mood: str = ""
    emotional_tone: str = ""
    visual_intent: str = ""


class ShotContext(BaseModel):
    """Extracted from Shot."""
    shot_type: str = ""
    camera_framing: str = ""
    camera_movement: str = ""
    subject: str = ""
    environment: str = ""
    emotion: str = ""
    description: str = ""
    asset_strategy: str = "image_to_video"
    duration_sec: float = 4.0


class FrameContext(BaseModel):
    """Extracted from FrameSpec."""
    frame_role: str = "start"
    composition: str = ""
    subject_position: str = ""
    camera_angle: str = ""
    lens_feel: str = ""
    lighting: str = ""
    mood: str = ""
    action_pose: str = ""
    background_description: str = ""
    continuity_notes: str = ""
    forbidden_elements: str = ""


class ProjectContext(BaseModel):
    """Extracted from Project settings."""
    width: int = 1920
    height: int = 1080
    aspect_ratio: str = "16:9"
    default_image_model: str = "fal"
    default_video_model: str = "runway"


class CompilerContext(BaseModel):
    """Full context bundle passed to compiler functions."""
    project: ProjectContext = Field(default_factory=ProjectContext)
    style: StyleContext = Field(default_factory=StyleContext)
    continuity: ContinuityContext = Field(default_factory=ContinuityContext)
    characters: list[CharacterContext] = Field(default_factory=list)
    scene: SceneContext = Field(default_factory=SceneContext)
    shot: ShotContext = Field(default_factory=ShotContext)
    frame: FrameContext = Field(default_factory=FrameContext)


class CompiledPrompt(BaseModel):
    """Output of the prompt compiler."""
    concise_prompt: str = Field(..., description="Short prompt (< 200 chars) for quick preview")
    detailed_prompt: str = Field(..., description="Full image generation prompt")
    video_prompt: str = Field(default="", description="Video generation prompt (motion-focused)")
    negative_prompt: str = Field(default="", description="Negative prompt")
    continuity_notes: str = Field(default="", description="Notes for cross-frame consistency")
    provider_options: dict = Field(
        default_factory=dict,
        description="Provider-specific hints (aspect_ratio, model, etc.)",
    )
