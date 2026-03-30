"""Pure-function prompt compiler.

All functions take plain Pydantic data objects (no DB, no async) so they are
trivially testable. The single entry point is :func:`compile_full`.
"""

from __future__ import annotations

from shared.prompt_compiler.types import (
    CharacterContext,
    CompiledPrompt,
    CompilerContext,
    ContinuityContext,
    FrameContext,
    ShotContext,
    StyleContext,
)


# ── Internal helpers ──────────────────────────────────


def _join(*parts: str, sep: str = ", ") -> str:
    return sep.join(p.strip() for p in parts if p and p.strip())


def _build_character_snippet(chars: list[CharacterContext]) -> str:
    if not chars:
        return ""
    snippets: list[str] = []
    for c in chars:
        parts: list[str] = []
        if c.visual_prompt:
            parts.append(c.visual_prompt)
        else:
            desc_parts: list[str] = []
            if c.appearance:
                desc_parts.append(c.appearance)
            if c.body_type:
                desc_parts.append(c.body_type)
            if c.skin_tone:
                desc_parts.append(c.skin_tone)
            if c.hair_description:
                desc_parts.append(c.hair_description)
            if c.outfit:
                desc_parts.append(c.outfit)
            if c.facial_traits:
                desc_parts.append(c.facial_traits)
            if desc_parts:
                parts.append(", ".join(desc_parts))
        if c.age_impression:
            parts.append(c.age_impression)
        if c.signature_props:
            parts.append(f"always with: {c.signature_props}")
        if c.pose_rules:
            parts.append(f"({c.pose_rules})")
        if parts:
            snippets.append(f"[{c.name or 'character'}] " + ", ".join(parts))
    return "; ".join(snippets)


def _build_scene_atmosphere(ctx: CompilerContext) -> str:
    scene = ctx.scene
    return _join(scene.setting, scene.mood, scene.emotional_tone)


def _build_camera_description(shot: ShotContext, frame: FrameContext) -> str:
    parts: list[str] = []
    if frame.camera_angle:
        parts.append(frame.camera_angle)
    elif shot.camera_framing:
        parts.append(shot.camera_framing)

    if frame.lens_feel:
        parts.append(frame.lens_feel)
    return _join(*parts)


# ── Continuity compilation ────────────────────────────


def compile_continuity_block(ctx: CompilerContext) -> str:
    """Build a continuity enforcement string from style anchors, character locks,
    and the project-level ContinuityProfile."""
    if not ctx.continuity.enabled:
        return ""

    parts: list[str] = []
    cont = ctx.continuity
    style = ctx.style

    # Style anchor (from preset or continuity profile)
    anchor = style.style_anchor or cont.style_anchor_summary
    if anchor:
        parts.append(f"STYLE ANCHOR: {anchor}")

    # Color consistency
    color_parts: list[str] = []
    if cont.color_palette_lock:
        color_parts.append(cont.color_palette_lock)
    elif style.color_palette:
        color_parts.append(style.color_palette)
    if style.color_temperature:
        color_parts.append(f"color temp: {style.color_temperature}")
    elif cont.color_temperature_range:
        color_parts.append(f"color temp range: {cont.color_temperature_range}")
    if color_parts:
        parts.append(f"COLOR LOCK: {', '.join(color_parts)}")

    # Lighting anchor
    light = cont.lighting_anchor or style.lighting_rules
    if light:
        parts.append(f"LIGHTING BASELINE: {light}")

    # Texture/depth
    tex_parts = [p for p in [style.texture_quality, style.depth_style] if p]
    if tex_parts:
        parts.append(f"SURFACE: {', '.join(tex_parts)}")

    # Environment consistency
    env = cont.environment_consistency or style.environment_rules
    if env:
        parts.append(f"ENVIRONMENT RULES: {env}")

    # Character locks
    char_locks: list[str] = []
    if cont.character_lock_notes:
        char_locks.append(cont.character_lock_notes)
    for c in ctx.characters:
        lock_parts: list[str] = []
        if c.forbidden_drift:
            lock_parts.append(c.forbidden_drift)
        elif c.forbidden_changes:
            lock_parts.append(c.forbidden_changes)
        if c.signature_props:
            lock_parts.append(f"always has: {c.signature_props}")
        if lock_parts:
            char_locks.append(f"[{c.name}] {'; '.join(lock_parts)}")
    if char_locks:
        parts.append(f"CHARACTER LOCK: {' | '.join(char_locks)}")

    # Temporal rules
    if cont.temporal_rules:
        parts.append(f"TEMPORAL: {cont.temporal_rules}")

    return " || ".join(parts) if parts else ""


def _build_continuity_negative(ctx: CompilerContext) -> list[str]:
    """Collect forbidden drift items for negative prompt."""
    items: list[str] = []
    cont = ctx.continuity
    if not cont.enabled:
        return items
    if cont.forbidden_global_drift:
        items.append(cont.forbidden_global_drift.strip())
    for c in ctx.characters:
        if c.forbidden_drift:
            items.append(c.forbidden_drift.strip())
    return items


# ── Public API ────────────────────────────────────────


def compile_image_prompt(ctx: CompilerContext) -> str:
    """Build a detailed image generation prompt from all context layers."""
    style = ctx.style
    shot = ctx.shot
    frame = ctx.frame

    segments: list[str] = []

    # 1. Style prefix
    if style.prompt_prefix:
        segments.append(style.prompt_prefix.rstrip(",").strip())

    # 2. Core visual description from shot
    if shot.description:
        segments.append(shot.description)

    # 3. Frame-specific composition & action
    frame_parts: list[str] = []
    if frame.composition:
        frame_parts.append(frame.composition)
    if frame.action_pose:
        frame_parts.append(frame.action_pose)
    if frame.subject_position:
        frame_parts.append(f"subject at {frame.subject_position}")
    if frame_parts:
        segments.append(_join(*frame_parts))

    # 4. Characters (now with extended identity fields)
    char_snippet = _build_character_snippet(ctx.characters)
    if char_snippet:
        segments.append(char_snippet)

    # 5. Camera
    cam = _build_camera_description(shot, frame)
    if cam:
        segments.append(cam)

    # 6. Lighting (frame > continuity anchor > style fallback)
    lighting = frame.lighting or ""
    if not lighting and ctx.continuity.enabled and ctx.continuity.lighting_anchor:
        lighting = ctx.continuity.lighting_anchor
    if not lighting and style.lighting_rules:
        lighting = style.lighting_rules
    if lighting:
        segments.append(lighting)

    # 7. Background
    if frame.background_description:
        segments.append(f"background: {frame.background_description}")
    elif shot.environment:
        segments.append(f"background: {shot.environment}")

    # 8. Mood / atmosphere
    atmosphere = _join(
        frame.mood or shot.emotion or "",
        _build_scene_atmosphere(ctx),
    )
    if atmosphere:
        segments.append(atmosphere)

    # 9. Style keywords & rendering + texture/depth
    style_parts = [style.style_keywords, style.rendering_style, style.color_palette]
    if style.texture_quality:
        style_parts.append(style.texture_quality)
    if style.depth_style:
        style_parts.append(style.depth_style)
    style_tail = _join(*[p for p in style_parts if p])
    if style_tail:
        segments.append(style_tail)

    # 10. Continuity enforcement block
    cont_block = compile_continuity_block(ctx)
    if cont_block:
        segments.append(f"[{cont_block}]")

    # 11. Style suffix
    if style.prompt_suffix:
        segments.append(style.prompt_suffix.strip())

    return _join(*segments)


def compile_concise_prompt(ctx: CompilerContext) -> str:
    """Build a short (~100–200 char) summary prompt."""
    shot = ctx.shot
    frame = ctx.frame
    style = ctx.style

    parts: list[str] = []
    if style.rendering_style:
        parts.append(style.rendering_style.split(",")[0].strip())
    if shot.description:
        desc = shot.description
        if len(desc) > 120:
            desc = desc[:117] + "..."
        parts.append(desc)
    elif frame.composition:
        parts.append(frame.composition[:100])

    if frame.mood or shot.emotion:
        parts.append(frame.mood or shot.emotion or "")

    return _join(*parts)


def compile_video_prompt(ctx: CompilerContext) -> str:
    """Build a motion-focused video generation prompt."""
    shot = ctx.shot
    frame = ctx.frame
    style = ctx.style

    segments: list[str] = []

    if style.prompt_prefix:
        segments.append(style.prompt_prefix.rstrip(",").strip())

    if shot.description:
        segments.append(shot.description)

    # Motion description
    motion_parts: list[str] = []
    if shot.camera_movement and shot.camera_movement != "static":
        motion_parts.append(f"camera motion: {shot.camera_movement}")
    if frame.action_pose:
        motion_parts.append(f"action: {frame.action_pose}")
    if motion_parts:
        segments.append(_join(*motion_parts))

    cam = _build_camera_description(shot, frame)
    if cam:
        segments.append(cam)

    if frame.background_description:
        segments.append(f"background: {frame.background_description}")

    atmosphere = _join(frame.mood or shot.emotion or "", _build_scene_atmosphere(ctx))
    if atmosphere:
        segments.append(atmosphere)

    style_tail = _join(style.style_keywords, style.rendering_style)
    if style_tail:
        segments.append(style_tail)

    # Continuity enforcement in video too
    cont_block = compile_continuity_block(ctx)
    if cont_block:
        segments.append(f"[{cont_block}]")

    if shot.duration_sec:
        segments.append(f"duration: {shot.duration_sec}s")

    return _join(*segments)


def compile_negative_prompt(ctx: CompilerContext) -> str:
    """Merge style negatives + frame forbidden elements + continuity drift."""
    parts: list[str] = []

    if ctx.style.negative_prompt:
        parts.append(ctx.style.negative_prompt.strip())

    if ctx.style.negative_rules:
        parts.append(ctx.style.negative_rules.strip())

    if ctx.frame.forbidden_elements:
        parts.append(ctx.frame.forbidden_elements.strip())

    for char in ctx.characters:
        if char.forbidden_changes:
            parts.append(char.forbidden_changes.strip())

    # Add continuity-derived drift prevention
    parts.extend(_build_continuity_negative(ctx))

    seen: set[str] = set()
    deduped: list[str] = []
    for part in parts:
        for token in part.split(","):
            t = token.strip().lower()
            if t and t not in seen:
                seen.add(t)
                deduped.append(token.strip())

    return ", ".join(deduped)


def compile_full(ctx: CompilerContext) -> CompiledPrompt:
    """Compile all prompt variants from context. Main entry point."""
    detailed = compile_image_prompt(ctx)
    concise = compile_concise_prompt(ctx)
    video = compile_video_prompt(ctx)
    negative = compile_negative_prompt(ctx)

    # Build continuity notes from frame + compiled block
    cont_notes_parts: list[str] = []
    if ctx.frame.continuity_notes:
        cont_notes_parts.append(ctx.frame.continuity_notes)
    cont_block = compile_continuity_block(ctx)
    if cont_block:
        cont_notes_parts.append(cont_block)
    continuity_notes = " | ".join(cont_notes_parts)

    provider_options: dict = {
        "aspect_ratio": ctx.project.aspect_ratio,
        "width": ctx.project.width,
        "height": ctx.project.height,
        "image_model": ctx.project.default_image_model,
        "video_model": ctx.project.default_video_model,
        "asset_strategy": ctx.shot.asset_strategy,
        "duration_sec": ctx.shot.duration_sec,
        "frame_role": ctx.frame.frame_role,
    }

    if ctx.style.name:
        provider_options["style_preset"] = ctx.style.name
    if ctx.style.style_anchor:
        provider_options["style_anchor"] = ctx.style.style_anchor

    return CompiledPrompt(
        concise_prompt=concise,
        detailed_prompt=detailed,
        video_prompt=video,
        negative_prompt=negative,
        continuity_notes=continuity_notes,
        provider_options=provider_options,
    )
