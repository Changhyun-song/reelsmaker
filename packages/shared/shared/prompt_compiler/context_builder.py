"""Build CompilerContext from ORM models.

Shared between API (prompts.py) and Worker (image handler).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.character_profile import CharacterProfile
from shared.models.continuity_profile import ContinuityProfile
from shared.models.frame_spec import FrameSpec
from shared.models.project import Project
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.models.style_preset import StylePreset
from shared.prompt_compiler.types import (
    CharacterContext,
    CompilerContext,
    ContinuityContext,
    FrameContext,
    ProjectContext,
    SceneContext,
    ShotContext,
    StyleContext,
)


def style_to_ctx(s: StylePreset | None) -> StyleContext:
    if s is None:
        return StyleContext()
    return StyleContext(
        name=s.name or "",
        style_keywords=s.style_keywords or "",
        color_palette=s.color_palette or "",
        rendering_style=s.rendering_style or "",
        camera_language=s.camera_language or "",
        lighting_rules=s.lighting_rules or "",
        negative_rules=s.negative_rules or "",
        prompt_prefix=s.prompt_prefix or "",
        prompt_suffix=s.prompt_suffix or "",
        negative_prompt=s.negative_prompt or "",
        style_anchor=s.style_anchor or "",
        color_temperature=s.color_temperature or "",
        texture_quality=s.texture_quality or "",
        depth_style=s.depth_style or "",
        environment_rules=s.environment_rules or "",
    )


def char_to_ctx(c: CharacterProfile) -> CharacterContext:
    return CharacterContext(
        name=c.name or "",
        role=c.role or "",
        appearance=c.appearance or "",
        outfit=c.outfit or "",
        age_impression=c.age_impression or "",
        facial_traits=c.facial_traits or "",
        pose_rules=c.pose_rules or "",
        forbidden_changes=c.forbidden_changes or "",
        visual_prompt=c.visual_prompt or "",
        body_type=c.body_type or "",
        hair_description=c.hair_description or "",
        skin_tone=c.skin_tone or "",
        signature_props=c.signature_props or "",
        forbidden_drift=c.forbidden_drift or "",
    )


def continuity_to_ctx(cp: ContinuityProfile | None) -> ContinuityContext:
    if cp is None:
        return ContinuityContext(enabled=False)
    return ContinuityContext(
        enabled=cp.enabled,
        color_palette_lock=cp.color_palette_lock or "",
        lighting_anchor=cp.lighting_anchor or "",
        color_temperature_range=cp.color_temperature_range or "",
        environment_consistency=cp.environment_consistency or "",
        style_anchor_summary=cp.style_anchor_summary or "",
        character_lock_notes=cp.character_lock_notes or "",
        forbidden_global_drift=cp.forbidden_global_drift or "",
        temporal_rules=cp.temporal_rules or "",
    )


def scene_to_ctx(sc: Scene) -> SceneContext:
    return SceneContext(
        title=sc.title or "",
        setting=sc.setting or "",
        mood=sc.mood or "",
        emotional_tone=sc.emotional_tone or "",
        visual_intent=sc.visual_intent or "",
    )


def shot_to_ctx(sh: Shot) -> ShotContext:
    return ShotContext(
        shot_type=sh.shot_type or "",
        camera_framing=sh.camera_framing or "",
        camera_movement=sh.camera_movement or "",
        subject=sh.subject or "",
        environment=sh.environment or "",
        emotion=sh.emotion or "",
        description=sh.description or "",
        asset_strategy=sh.asset_strategy or "image_to_video",
        duration_sec=sh.duration_sec or 4.0,
    )


def frame_to_ctx(f: FrameSpec) -> FrameContext:
    return FrameContext(
        frame_role=f.frame_role or "start",
        composition=f.composition or "",
        subject_position=f.subject_position or "",
        camera_angle=f.camera_angle or "",
        lens_feel=f.lens_feel or "",
        lighting=f.lighting or "",
        mood=f.mood or "",
        action_pose=f.action_pose or "",
        background_description=f.background_description or "",
        continuity_notes=f.continuity_notes or "",
        forbidden_elements=f.forbidden_elements or "",
    )


def project_to_ctx(p: Project) -> ProjectContext:
    s = p.settings or {}
    return ProjectContext(
        width=s.get("width", 1920),
        height=s.get("height", 1080),
        aspect_ratio=s.get("aspect_ratio", "16:9"),
        default_image_model=s.get("default_image_model", "fal"),
        default_video_model=s.get("default_video_model", "runway"),
    )


async def _load_project_context(
    project_id: UUID,
    db: AsyncSession,
) -> tuple:
    """Load project, style, characters, and continuity profile."""
    project = (
        await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.active_style_preset))
        )
    ).scalar_one_or_none()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    characters = list(
        (
            await db.execute(
                select(CharacterProfile).where(
                    CharacterProfile.project_id == project_id
                )
            )
        ).scalars().all()
    )

    continuity = (
        await db.execute(
            select(ContinuityProfile).where(
                ContinuityProfile.project_id == project_id
            )
        )
    ).scalar_one_or_none()

    return project, characters, continuity


async def build_compiler_context(
    project_id: UUID,
    frame_id: UUID,
    db: AsyncSession,
) -> CompilerContext:
    """Fetch all related entities and assemble a CompilerContext (frame-level)."""

    frame = (
        await db.execute(select(FrameSpec).where(FrameSpec.id == frame_id))
    ).scalar_one_or_none()
    if not frame:
        raise ValueError(f"FrameSpec {frame_id} not found")

    shot = (
        await db.execute(select(Shot).where(Shot.id == frame.shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise ValueError(f"Shot {frame.shot_id} not found")

    scene = (
        await db.execute(select(Scene).where(Scene.id == shot.scene_id))
    ).scalar_one_or_none()
    if not scene:
        raise ValueError(f"Scene {shot.scene_id} not found")

    project, characters, continuity = await _load_project_context(project_id, db)

    return CompilerContext(
        project=project_to_ctx(project),
        style=style_to_ctx(project.active_style_preset),
        continuity=continuity_to_ctx(continuity),
        characters=[char_to_ctx(c) for c in characters],
        scene=scene_to_ctx(scene),
        shot=shot_to_ctx(shot),
        frame=frame_to_ctx(frame),
    )


async def build_shot_compiler_context(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession,
) -> CompilerContext:
    """Build CompilerContext at shot level, using the start frame if available."""

    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise ValueError(f"Shot {shot_id} not found")

    scene = (
        await db.execute(select(Scene).where(Scene.id == shot.scene_id))
    ).scalar_one_or_none()
    if not scene:
        raise ValueError(f"Scene {shot.scene_id} not found")

    project, characters, continuity = await _load_project_context(project_id, db)

    start_frame = (
        await db.execute(
            select(FrameSpec)
            .where(FrameSpec.shot_id == shot_id)
            .order_by(FrameSpec.order_index)
            .limit(1)
        )
    ).scalar_one_or_none()

    frame_ctx = frame_to_ctx(start_frame) if start_frame else FrameContext()

    return CompilerContext(
        project=project_to_ctx(project),
        style=style_to_ctx(project.active_style_preset),
        continuity=continuity_to_ctx(continuity),
        characters=[char_to_ctx(c) for c in characters],
        scene=scene_to_ctx(scene),
        shot=shot_to_ctx(shot),
        frame=frame_ctx,
    )


def build_continuity_text_block(
    style: StylePreset | None,
    characters: list[CharacterProfile],
    continuity: ContinuityProfile | None,
) -> str:
    """Build a plain-text continuity context block for injection into AI planner
    prompts (shot/frame planners). No CompilerContext needed — works from ORM models."""
    lines: list[str] = []

    # Style anchor
    if style:
        anchor = style.style_anchor or ""
        if anchor:
            lines.append(f"STYLE ANCHOR: {anchor}")
        if style.color_palette:
            lines.append(f"COLOR PALETTE: {style.color_palette}")
        if style.color_temperature:
            lines.append(f"COLOR TEMPERATURE: {style.color_temperature}")
        if style.lighting_rules:
            lines.append(f"LIGHTING RULES: {style.lighting_rules}")
        if style.texture_quality:
            lines.append(f"TEXTURE: {style.texture_quality}")
        if style.depth_style:
            lines.append(f"DEPTH: {style.depth_style}")
        if style.environment_rules:
            lines.append(f"ENVIRONMENT RULES: {style.environment_rules}")
        if style.negative_rules:
            lines.append(f"STYLE NEGATIVES: {style.negative_rules}")

    # Character anchors
    for c in characters:
        char_parts: list[str] = []
        for attr in [c.appearance, c.body_type, c.skin_tone, c.hair_description,
                     c.outfit, c.facial_traits]:
            if attr:
                char_parts.append(attr)
        if c.signature_props:
            char_parts.append(f"always has: {c.signature_props}")
        if c.forbidden_drift:
            char_parts.append(f"MUST NOT CHANGE: {c.forbidden_drift}")
        elif c.forbidden_changes:
            char_parts.append(f"MUST NOT CHANGE: {c.forbidden_changes}")
        if char_parts:
            lines.append(f"CHARACTER [{c.name}]: {'; '.join(char_parts)}")

    # Continuity profile
    if continuity and continuity.enabled:
        if continuity.color_palette_lock:
            lines.append(f"COLOR LOCK: {continuity.color_palette_lock}")
        if continuity.lighting_anchor:
            lines.append(f"LIGHTING ANCHOR: {continuity.lighting_anchor}")
        if continuity.environment_consistency:
            lines.append(f"ENVIRONMENT CONSISTENCY: {continuity.environment_consistency}")
        if continuity.character_lock_notes:
            lines.append(f"CHARACTER LOCK: {continuity.character_lock_notes}")
        if continuity.forbidden_global_drift:
            lines.append(f"FORBIDDEN DRIFT: {continuity.forbidden_global_drift}")
        if continuity.temporal_rules:
            lines.append(f"TEMPORAL RULES: {continuity.temporal_rules}")

    return "\n".join(lines)
