"""Quality-first, provider-aware prompt compiler.

All functions take plain Pydantic data objects (no DB, no async) so they are
trivially testable. The single entry point is :func:`compile_full`.

Prompt structure follows a block-based sentence order instead of comma soup:
  A. Core shot sentence
  B. Composition + subject position
  C. Character identity lock
  D. Camera + lens
  E. Lighting
  F. Background layers
  G. Mood + atmosphere
  H. Style / render keywords
  I. Continuity block
"""

from __future__ import annotations

import re

from shared.prompt_compiler.types import (
    CharacterContext,
    CompiledPrompt,
    CompilerContext,
    ContinuityContext,
    FrameContext,
    QualityMode,
    ShotContext,
    StyleContext,
)

# ── Negative prompt baselines ────────────────────────

IMAGE_NEGATIVE_BASELINE = [
    "text", "watermark", "logo", "blurry", "low detail", "extra fingers",
    "extra limbs", "bad anatomy", "duplicated subject", "deformed face",
    "asymmetrical eyes", "floating objects", "inconsistent shadows",
]

VIDEO_NEGATIVE_BASELINE = [
    "temporal flicker", "frame jitter", "morphing face", "warped hands",
    "rubber limbs", "sudden camera shake", "inconsistent lighting",
    "subtitle text", "watermark", "compression artifacts",
]

# Low-priority style tokens that can be trimmed when prompt is too long
_LOW_PRIORITY_STYLE_WORDS = {
    "masterpiece", "best quality", "ultra detailed", "8k", "4k", "uhd",
    "photorealistic", "hyperrealistic", "professional", "award-winning",
    "trending on artstation", "highly detailed", "sharp focus",
    "studio quality", "hdr", "octane render", "unreal engine",
}

_MAX_PROMPT_LENGTH = 1500

# ── Motion sentence templates ────────────────────────

_MOTION_TEMPLATES: dict[str, str] = {
    "static": "Subtle changes only — slight pose shifts and natural micro-expressions, no camera movement.",
    "slow_pan_left": "Smooth lateral reveal panning left, subject scale stays constant as background slides rightward.",
    "slow_pan_right": "Smooth lateral reveal panning right, subject scale stays constant as background slides leftward.",
    "pan_left": "Camera pans left with moderate speed, maintaining subject framing while revealing new environment.",
    "pan_right": "Camera pans right with moderate speed, maintaining subject framing while revealing new environment.",
    "tilt_up": "Camera tilts upward gradually, revealing higher elements while lower portion exits frame.",
    "tilt_down": "Camera tilts downward gradually, revealing lower elements while upper portion exits frame.",
    "dolly_in": "Camera physically moves closer — subject grows larger in frame, background recedes with natural parallax.",
    "dolly_out": "Camera physically pulls back — subject becomes smaller, more environment revealed with depth perspective.",
    "push_in": "Steady push toward subject, increasing intimacy and focus, background gradually blurs.",
    "zoom_in": "Tighter framing without perspective shift — subject fills more frame, no parallax change.",
    "zoom_out": "Wider framing without perspective shift — more environment visible, subject scale decreases.",
    "tracking_left": "Camera tracks laterally left alongside subject, maintaining relative position with parallax shift.",
    "tracking_right": "Camera tracks laterally right alongside subject, maintaining relative position with parallax shift.",
    "tracking_forward": "Camera moves forward tracking subject, background parallax reveals spatial depth.",
    "crane_up": "Camera rises vertically, creating an ascending reveal of the scene from below.",
    "crane_down": "Camera descends vertically, settling into the scene from above.",
    "handheld": "Organic handheld camera movement with natural micro-shake, creating documentary intimacy.",
    "orbit_left": "Camera orbits left around subject, maintaining focus while background rotates behind.",
    "orbit_right": "Camera orbits right around subject, maintaining focus while background rotates behind.",
}


# ── Internal helpers ──────────────────────────────────


def _join(*parts: str, sep: str = ", ") -> str:
    return sep.join(p.strip() for p in parts if p and p.strip())


def _sentence_join(*parts: str) -> str:
    """Join non-empty parts with period-space, forming block sentences."""
    cleaned = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not p.endswith((".","!","?")):
            p = p + "."
        cleaned.append(p)
    return " ".join(cleaned)


def _dedupe_tokens(text: str, sep: str = ",") -> str:
    """Remove duplicate comma-separated tokens (case-insensitive)."""
    seen: set[str] = set()
    result: list[str] = []
    for token in text.split(sep):
        t = token.strip()
        key = t.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(t)
    return f"{sep} ".join(result)


def _trim_prompt(prompt: str, max_len: int = _MAX_PROMPT_LENGTH) -> str:
    """Trim prompt to max_len, removing low-priority style keywords first."""
    if len(prompt) <= max_len:
        return prompt

    tokens = [t.strip() for t in prompt.split(",")]
    high: list[str] = []
    low: list[str] = []
    for t in tokens:
        if t.lower() in _LOW_PRIORITY_STYLE_WORDS:
            low.append(t)
        else:
            high.append(t)

    result = ", ".join(high)
    if len(result) <= max_len:
        remaining = max_len - len(result) - 2
        for l_tok in low:
            candidate = result + ", " + l_tok
            if len(candidate) <= max_len:
                result = candidate
            else:
                break
        return result

    return result[:max_len - 3] + "..."


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


def _build_camera_description(shot: ShotContext, frame: FrameContext) -> str:
    parts: list[str] = []
    if frame.camera_angle:
        parts.append(frame.camera_angle)
    elif shot.camera_framing:
        parts.append(shot.camera_framing)

    if frame.lens_feel:
        parts.append(frame.lens_feel)
    return _join(*parts)


def _build_scene_atmosphere(ctx: CompilerContext) -> str:
    scene = ctx.scene
    return _join(scene.setting, scene.mood, scene.emotional_tone)


def _quality_render_keywords(mode: QualityMode) -> str:
    if mode == "speed":
        return ""
    if mode == "quality":
        return "cinematic 8K, photorealistic detail, ray-traced global illumination"
    return "cinematic quality, sharp detail"


def _build_motion_sentence(
    camera_motion: str,
    asset_strategy: str,
    duration_sec: float,
) -> str:
    """Build a motion description sentence based on camera motion type."""
    motion = camera_motion.lower().strip() if camera_motion else "static"

    if asset_strategy == "still_image":
        return "Static frame — no motion, hold composition steady."

    template = _MOTION_TEMPLATES.get(motion)
    if not template:
        if "pan" in motion:
            template = f"Camera {motion.replace('_', ' ')}, smooth lateral movement maintaining subject framing."
        elif "track" in motion:
            template = f"Camera {motion.replace('_', ' ')}, following subject with parallax depth."
        else:
            template = _MOTION_TEMPLATES["static"]

    if asset_strategy == "direct_video":
        template = template + " Emphasize fluid, continuous action with natural motion dynamics."

    return template


# ── Continuity compilation ────────────────────────────


def compile_continuity_block(ctx: CompilerContext) -> str:
    """Build a continuity enforcement string from style anchors, character locks,
    and the project-level ContinuityProfile."""
    if not ctx.continuity.enabled:
        return ""

    parts: list[str] = []
    cont = ctx.continuity
    style = ctx.style

    anchor = style.style_anchor or cont.style_anchor_summary
    if anchor:
        parts.append(f"STYLE ANCHOR: {anchor}")

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

    light = cont.lighting_anchor or style.lighting_rules
    if light:
        parts.append(f"LIGHTING BASELINE: {light}")

    tex_parts = [p for p in [style.texture_quality, style.depth_style] if p]
    if tex_parts:
        parts.append(f"SURFACE: {', '.join(tex_parts)}")

    env = cont.environment_consistency or style.environment_rules
    if env:
        parts.append(f"ENVIRONMENT RULES: {env}")

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
    """Build a detailed image generation prompt using block-based sentence structure.

    Block order:
      A. Core shot sentence
      B. Composition + subject position
      C. Character identity lock
      D. Camera + lens
      E. Lighting
      F. Background layers
      G. Mood + atmosphere
      H. Style / render keywords
      I. Continuity block
    """
    style = ctx.style
    shot = ctx.shot
    frame = ctx.frame
    mode = ctx.quality_mode

    blocks: list[str] = []

    # Style prefix (if present)
    if style.prompt_prefix:
        blocks.append(style.prompt_prefix.rstrip(",").strip())

    # A. Core shot sentence
    if shot.description:
        blocks.append(shot.description)

    # B. Composition + subject position
    comp_parts: list[str] = []
    if frame.composition:
        comp_parts.append(frame.composition)
    if frame.subject_position:
        comp_parts.append(f"Subject placed at {frame.subject_position}")
    if frame.action_pose:
        comp_parts.append(frame.action_pose)
    if comp_parts:
        blocks.append(_sentence_join(*comp_parts))

    # C. Character identity lock
    char_snippet = _build_character_snippet(ctx.characters)
    if char_snippet:
        blocks.append(char_snippet)

    # D. Camera + lens
    cam = _build_camera_description(shot, frame)
    if cam:
        blocks.append(cam)

    # E. Lighting (frame > continuity anchor > style fallback)
    lighting = frame.lighting or ""
    if not lighting and ctx.continuity.enabled and ctx.continuity.lighting_anchor:
        lighting = ctx.continuity.lighting_anchor
    if not lighting and style.lighting_rules:
        lighting = style.lighting_rules
    if lighting:
        blocks.append(lighting)

    # F. Background layers
    bg = frame.background_description or shot.environment
    if bg:
        blocks.append(f"Background: {bg}")

    # G. Mood + atmosphere
    mood_parts: list[str] = []
    if frame.mood:
        mood_parts.append(frame.mood)
    elif shot.emotion:
        mood_parts.append(shot.emotion)
    scene_atmo = _build_scene_atmosphere(ctx)
    if scene_atmo:
        mood_parts.append(scene_atmo)
    if mood_parts:
        blocks.append(_join(*mood_parts))

    # H. Style / render keywords + quality mode boost
    style_parts = [p for p in [
        style.style_keywords, style.rendering_style, style.color_palette,
        style.texture_quality, style.depth_style,
    ] if p]
    quality_kw = _quality_render_keywords(mode)
    if quality_kw:
        style_parts.append(quality_kw)
    if style_parts:
        blocks.append(_join(*style_parts))

    # I. Continuity enforcement block
    cont_block = compile_continuity_block(ctx)
    if cont_block:
        blocks.append(f"[{cont_block}]")

    # Style suffix
    if style.prompt_suffix:
        blocks.append(style.prompt_suffix.strip())

    raw = _join(*blocks, sep=". ") if mode == "quality" else _join(*blocks)
    deduped = _dedupe_tokens(raw)
    return _trim_prompt(deduped)


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
    """Build a motion-focused video generation prompt with camera-aware sentences."""
    shot = ctx.shot
    frame = ctx.frame
    style = ctx.style
    mode = ctx.quality_mode

    segments: list[str] = []

    if style.prompt_prefix:
        segments.append(style.prompt_prefix.rstrip(",").strip())

    # Core visual description
    if shot.description:
        segments.append(shot.description)

    # Motion sentence based on camera_motion + asset_strategy
    motion_sentence = _build_motion_sentence(
        shot.camera_movement or "static",
        shot.asset_strategy or "image_to_video",
        shot.duration_sec,
    )
    segments.append(motion_sentence)

    # Action/pose
    if frame.action_pose:
        segments.append(f"Action: {frame.action_pose}")

    # Camera + lens
    cam = _build_camera_description(shot, frame)
    if cam:
        segments.append(cam)

    # Background
    if frame.background_description:
        segments.append(f"Background: {frame.background_description}")

    # Mood + atmosphere
    mood_parts: list[str] = []
    if frame.mood:
        mood_parts.append(frame.mood)
    elif shot.emotion:
        mood_parts.append(shot.emotion)
    scene_atmo = _build_scene_atmosphere(ctx)
    if scene_atmo:
        mood_parts.append(scene_atmo)
    if mood_parts:
        segments.append(_join(*mood_parts))

    # Style keywords
    style_tail = _join(style.style_keywords, style.rendering_style)
    if mode == "quality" and style_tail:
        style_tail += ", cinematic motion, smooth temporal coherence"
    if style_tail:
        segments.append(style_tail)

    # Continuity enforcement
    cont_block = compile_continuity_block(ctx)
    if cont_block:
        segments.append(f"[{cont_block}]")

    # Duration always last
    if shot.duration_sec:
        segments.append(f"Duration: {shot.duration_sec:.1f}s")

    raw = _join(*segments)
    return _dedupe_tokens(raw)


def compile_negative_prompt(
    ctx: CompilerContext,
    *,
    media_type: str = "image",
) -> str:
    """Merge baseline negatives + style negatives + frame forbidden elements +
    continuity drift prevention. Deduplicated."""
    parts: list[str] = []

    # Baseline cluster
    if media_type == "video":
        parts.extend(VIDEO_NEGATIVE_BASELINE)
    else:
        parts.extend(IMAGE_NEGATIVE_BASELINE)

    # Style negatives
    if ctx.style.negative_prompt:
        parts.extend(t.strip() for t in ctx.style.negative_prompt.split(",") if t.strip())
    if ctx.style.negative_rules:
        parts.extend(t.strip() for t in ctx.style.negative_rules.split(",") if t.strip())

    # Frame forbidden elements
    if ctx.frame.forbidden_elements:
        parts.extend(t.strip() for t in ctx.frame.forbidden_elements.split(",") if t.strip())

    # Character forbidden changes
    for char in ctx.characters:
        if char.forbidden_changes:
            parts.extend(t.strip() for t in char.forbidden_changes.split(",") if t.strip())

    # Continuity-derived drift prevention
    for drift in _build_continuity_negative(ctx):
        parts.extend(t.strip() for t in drift.split(",") if t.strip())

    # Deduplicate (case-insensitive)
    seen: set[str] = set()
    deduped: list[str] = []
    for token in parts:
        key = token.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(token.strip())

    return ", ".join(deduped)


def compile_full(ctx: CompilerContext) -> CompiledPrompt:
    """Compile all prompt variants from context. Main entry point."""
    detailed = compile_image_prompt(ctx)
    concise = compile_concise_prompt(ctx)
    video = compile_video_prompt(ctx)
    negative_image = compile_negative_prompt(ctx, media_type="image")
    negative_video = compile_negative_prompt(ctx, media_type="video")

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
        "quality_mode": ctx.quality_mode,
        "negative_video": negative_video,
    }

    if ctx.style.name:
        provider_options["style_preset"] = ctx.style.name
    if ctx.style.style_anchor:
        provider_options["style_anchor"] = ctx.style.style_anchor

    return CompiledPrompt(
        concise_prompt=concise,
        detailed_prompt=detailed,
        video_prompt=video,
        negative_prompt=negative_image,
        continuity_notes=continuity_notes,
        provider_options=provider_options,
    )
