"""Shot planning handlers.

``handle_shot_plan``        Scene → Shot[] breakdown
``handle_shot_regenerate``  single Shot regeneration in context
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select, delete

from shared.config import get_settings
from shared.database import async_session_factory
from shared.models.character_profile import CharacterProfile
from shared.models.continuity_profile import ContinuityProfile
from shared.models.project import Project
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.providers import ProviderRequest, generate_validated
from shared.providers.claude_text import ClaudeTextProvider
from shared.providers.logger import log_provider_run
from shared.prompt_compiler.context_builder import build_continuity_text_block
from shared.schemas.contracts import ShotBreakdownOutput, SingleShotOutput

logger = logging.getLogger("reelsmaker.handlers.shot")

settings = get_settings()

# ── System prompts ────────────────────────────────────

_SHOT_PLAN_SYSTEM = """\
You are an expert cinematographer AI for short-form video. Decompose a scene into
individual shots — each 2-8 seconds of continuous camera with a single setup.

## REQUIRED FIELDS PER SHOT

| Field | Rules |
|-------|-------|
| shot_index | 0-based sequential |
| purpose | What this shot achieves: "establish the workspace environment", "reveal the product close-up", "show emotional reaction to news". NOT vague like "continue" or "transition". Min 5 chars. |
| duration_sec | 2-8 seconds preferred. 1.5-15 allowed. |
| shot_type | One of: establishing, insert, reaction, action, cutaway, over_the_shoulder, point_of_view, montage_element, detail, reveal, transition, title_card |
| camera_framing | One of: extreme_wide, wide, medium_wide, medium, medium_close_up, close_up, extreme_close_up, overhead, low_angle, birds_eye |
| camera_motion | One of: static, slow_pan_left, slow_pan_right, pan_left, pan_right, tilt_up, tilt_down, dolly_in, dolly_out, tracking_left, tracking_right, tracking_forward, crane_up, crane_down, handheld, orbit_left, orbit_right, zoom_in, zoom_out, push_in |
| subject | Main visual subject, English, SPECIFIC: "woman in navy blazer holding tablet" not "a person". Min 5 chars. |
| environment | Background details, English, SPECIFIC: "modern open-plan office, floor-to-ceiling windows, city skyline at dusk" not "an office". Min 5 chars. |
| emotion | Emotional quality: "focused determination", "gentle wonder", "rising excitement" |
| narration_segment | The exact portion of scene narration that plays over this shot (original language). All shots' narration_segments concatenated must = full scene narration. |
| transition_in | One of: cut, fade_in, dissolve_in, wipe_in |
| transition_out | One of: cut, fade_out, dissolve_out, wipe_out |
| asset_strategy | image_to_video (default for most), still_image (static/title), direct_video (complex motion), mixed |
| description | CRITICAL FIELD — standalone image/video prompt in English, ≥30 chars. Must include: subject + action/pose + environment + lighting hint + mood. Example: "Close-up of hands typing on mechanical keyboard, warm desk lamp illumination from left, shallow depth of field, focused productivity mood, modern minimalist desk setup, 8k cinematic" |

Also output **total_duration_sec** (sum of all shot durations).

## SHOT RHYTHM RULES
- Never use the same camera_framing for 3+ consecutive shots.
- Alternate between closer and wider framings to create visual rhythm.
- First shot should usually be wider (establishing), last shot should feel conclusive.
- Match camera_motion to emotional intensity: static = calm, dolly_in = focus,
  handheld = tension, slow_pan = exploration.

## ASSET STRATEGY GUIDE
- image_to_video: Most common. Generate a still frame, then animate it. Best for
  shots with simple/predictable motion (pan, zoom, subtle movement).
- still_image: Title cards, text overlays, static B-roll, infographic-style shots.
- direct_video: Complex action, multiple moving subjects, fluid motion.

## DURATION RULES
- total_duration_sec must be within ±10% of scene duration.
- Short scenes (≤10s): 2-3 shots.
- Medium scenes (10-20s): 3-5 shots.
- Long scenes (20-40s): 4-8 shots.

## BANNED
- description shorter than 30 characters.
- subject like "the subject" / "a person" / "someone" — must be SPECIFIC.
- environment like "a place" / "background" / "some location".
- Consecutive identical camera_framing values (must vary).
- narration_segment that doesn't come from the scene's actual narration text.

Output ONLY valid JSON — no markdown fences, no commentary."""

_SHOT_REGEN_SYSTEM = """\
You are an expert cinematographer AI. Regenerate ONE shot within a scene.

Your regenerated shot must:
1. Keep the same narration_segment (exact words, only punctuation may change).
2. Keep approximately the same duration (±1 second).
3. IMPROVE: description specificity (≥30 chars), subject concreteness, camera work.
4. Use DIFFERENT camera_framing from the adjacent shots (check context).
5. Ensure visual continuity: subject appearance, lighting direction, color temperature
   must match the surrounding shots.

The description field must be a standalone image generation prompt with:
subject + action/pose + environment + lighting + mood + style.

Output ONLY valid JSON — no markdown fences, no commentary."""


# ── Helpers ───────────────────────────────────────────


def _get_provider() -> ClaudeTextProvider:
    return ClaudeTextProvider(
        api_key=settings.anthropic_api_key,
        default_model=settings.claude_model,
        timeout_sec=settings.provider_timeout_sec,
    )


async def _update_job_progress(job_id: str, progress: int) -> None:
    from shared.models.job import Job

    async with async_session_factory() as session:
        result = await session.execute(
            select(Job).where(Job.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job:
            job.progress = progress
            await session.commit()


# ── Handler: shot_plan ────────────────────────────────


async def handle_shot_plan(job_id: str, **params) -> dict:
    """Break a Scene into shots."""
    project_id: str = params["project_id"]
    scene_id: str = params["scene_id"]

    async with async_session_factory() as session:
        scene = (
            await session.execute(
                select(Scene).where(Scene.id == uuid.UUID(scene_id))
            )
        ).scalar_one()

        # Load continuity context
        from sqlalchemy.orm import selectinload
        project = (
            await session.execute(
                select(Project)
                .where(Project.id == uuid.UUID(project_id))
                .options(selectinload(Project.active_style_preset))
            )
        ).scalar_one_or_none()
        characters = list(
            (await session.execute(
                select(CharacterProfile).where(CharacterProfile.project_id == uuid.UUID(project_id))
            )).scalars().all()
        )
        continuity = (
            await session.execute(
                select(ContinuityProfile).where(ContinuityProfile.project_id == uuid.UUID(project_id))
            )
        ).scalar_one_or_none()

    continuity_block = build_continuity_text_block(
        project.active_style_preset if project else None,
        characters,
        continuity,
    )

    scene_duration = scene.duration_estimate_sec or 15
    narration = scene.narration_text or ""
    visual_intent = scene.visual_intent or ""
    setting = scene.setting or ""
    mood = scene.mood or ""
    emotional_tone = scene.emotional_tone or ""

    provider = _get_provider()

    schema_hint = json.dumps(
        {
            "shots": [
                {
                    "shot_index": 0,
                    "purpose": "...",
                    "duration_sec": 4,
                    "shot_type": "establishing",
                    "camera_framing": "wide",
                    "camera_motion": "slow_pan_right",
                    "subject": "...",
                    "environment": "...",
                    "emotion": "...",
                    "narration_segment": "...",
                    "transition_in": "cut",
                    "transition_out": "cut",
                    "asset_strategy": "image_to_video",
                    "description": "...",
                }
            ],
            "total_duration_sec": 0,
        },
        ensure_ascii=False,
    )

    continuity_section = ""
    if continuity_block:
        continuity_section = (
            f"\n## CONTINUITY CONTEXT (must be respected in all shots)\n"
            f"{continuity_block}\n"
        )

    user_prompt = (
        f"## SCENE CONTEXT\n"
        f"- Title: {scene.title or 'Untitled'}\n"
        f"- Duration target: {scene_duration} seconds\n"
        f"- Purpose: {scene.purpose or 'N/A'}\n"
        f"- Setting: {setting}\n"
        f"- Mood: {mood}\n"
        f"- Emotional tone: {emotional_tone}\n"
        f"- Visual intent: {visual_intent}\n"
        f"{continuity_section}\n"
        f"## SCENE NARRATION (split into narration_segments across shots)\n"
        f"{narration}\n\n"
        f"## TASK\n"
        f"Decompose into shots. Each shot 2-8 seconds.\n"
        f"- total_duration_sec must ≈ {scene_duration}s (±10%)\n"
        f"- All narration_segments concatenated = full narration above\n"
        f"- Vary camera_framing between shots (no 3+ identical consecutive)\n"
        f"- description must be ≥30 chars, standalone image generation prompt\n"
        f"- Respect all CONTINUITY CONTEXT rules above\n\n"
        f"Output JSON matching:\n{schema_hint}"
    )

    request = ProviderRequest(
        system_prompt=_SHOT_PLAN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.6,
        max_tokens=8192,
    )

    await _update_job_progress(job_id, 10)

    try:
        response, result = await generate_validated(
            provider, request, ShotBreakdownOutput, max_attempts=3
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="shot_plan",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="shot_plan",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 60)

    # Duration validation
    drift = abs(result.total_duration_sec - scene_duration) / max(scene_duration, 1)
    duration_warning = None
    if drift > 0.1:
        duration_warning = (
            f"Shot total {result.total_duration_sec:.1f}s "
            f"deviates {drift:.0%} from scene {scene_duration}s"
        )
        logger.warning("shot_plan %s: %s", job_id, duration_warning)

    # Check individual shots for out-of-range durations
    clamped = 0
    for item in result.shots:
        if item.duration_sec < 1:
            item.duration_sec = 2.0
            clamped += 1
        elif item.duration_sec > 15:
            item.duration_sec = 8.0
            clamped += 1

    # Delete existing shots for this scene, insert new ones
    async with async_session_factory() as session:
        await session.execute(
            delete(Shot).where(Shot.scene_id == uuid.UUID(scene_id))
        )

        for item in result.shots:
            shot = Shot(
                scene_id=uuid.UUID(scene_id),
                order_index=item.shot_index,
                shot_type=item.shot_type,
                description=item.description,
                camera_movement=item.camera_motion,
                duration_sec=item.duration_sec,
                status="drafted",
                purpose=item.purpose,
                camera_framing=item.camera_framing,
                subject=item.subject,
                environment=item.environment,
                emotion=item.emotion,
                narration_segment=item.narration_segment,
                transition_in=item.transition_in,
                transition_out=item.transition_out,
                asset_strategy=item.asset_strategy,
                plan_json=item.model_dump(),
            )
            session.add(shot)

        await session.commit()

    await _update_job_progress(job_id, 100)

    return {
        "scene_id": scene_id,
        "shots_count": len(result.shots),
        "total_duration_sec": result.total_duration_sec,
        "scene_duration_sec": scene_duration,
        "duration_warning": duration_warning,
        "clamped_shots": clamped,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }


# ── Handler: shot_regenerate ──────────────────────────


async def handle_shot_regenerate(job_id: str, **params) -> dict:
    """Regenerate a single shot in context."""
    project_id: str = params["project_id"]
    shot_id: str = params["shot_id"]
    scene_id: str = params["scene_id"]

    async with async_session_factory() as session:
        target_shot = (
            await session.execute(select(Shot).where(Shot.id == uuid.UUID(shot_id)))
        ).scalar_one()

        all_shots = (
            await session.execute(
                select(Shot)
                .where(Shot.scene_id == uuid.UUID(scene_id))
                .order_by(Shot.order_index)
            )
        ).scalars().all()

        scene = (
            await session.execute(
                select(Scene).where(Scene.id == uuid.UUID(scene_id))
            )
        ).scalar_one()

    context_lines: list[str] = []
    for s in all_shots:
        marker = " <<<< REGENERATE THIS SHOT" if str(s.id) == shot_id else ""
        context_lines.append(
            f"[Shot {s.order_index}]{marker}\n"
            f"  Type: {s.shot_type} | Framing: {s.camera_framing} | Motion: {s.camera_movement}\n"
            f"  Duration: {s.duration_sec}s | Strategy: {s.asset_strategy}\n"
            f"  Subject: {s.subject or 'N/A'}\n"
            f"  Description: {s.description or 'N/A'}"
        )

    schema_hint = json.dumps(
        {
            "purpose": "...",
            "duration_sec": 4,
            "shot_type": "...",
            "camera_framing": "...",
            "camera_motion": "...",
            "subject": "...",
            "environment": "...",
            "emotion": "...",
            "narration_segment": "...",
            "transition_in": "cut",
            "transition_out": "cut",
            "asset_strategy": "image_to_video",
            "description": "...",
        },
        ensure_ascii=False,
    )

    user_prompt = (
        f"Scene: {scene.title or 'Untitled'} ({scene.duration_estimate_sec or 15}s)\n"
        f"Scene narration: {scene.narration_text or 'N/A'}\n\n"
        f"=== ALL SHOTS ===\n"
        + "\n\n".join(context_lines)
        + f"\n=== END ===\n\n"
        f"Regenerate the shot marked with <<<< REGENERATE THIS SHOT.\n"
        f"Keep approximately {target_shot.duration_sec or 4}s duration.\n"
        f"Output JSON matching:\n{schema_hint}"
    )

    provider = _get_provider()
    request = ProviderRequest(
        system_prompt=_SHOT_REGEN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=2048,
    )

    await _update_job_progress(job_id, 20)

    try:
        response, result = await generate_validated(
            provider, request, SingleShotOutput, max_attempts=3
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="shot_regenerate",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="shot_regenerate",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 70)

    async with async_session_factory() as session:
        shot = (
            await session.execute(select(Shot).where(Shot.id == uuid.UUID(shot_id)))
        ).scalar_one()

        shot.purpose = result.purpose
        shot.duration_sec = result.duration_sec
        shot.shot_type = result.shot_type
        shot.camera_framing = result.camera_framing
        shot.camera_movement = result.camera_motion
        shot.subject = result.subject
        shot.environment = result.environment
        shot.emotion = result.emotion
        shot.narration_segment = result.narration_segment
        shot.transition_in = result.transition_in
        shot.transition_out = result.transition_out
        shot.asset_strategy = result.asset_strategy
        shot.description = result.description
        shot.status = "drafted"
        shot.plan_json = result.model_dump()

        await session.commit()

    await _update_job_progress(job_id, 100)

    return {
        "shot_id": shot_id,
        "shot_type": result.shot_type,
        "duration_sec": result.duration_sec,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }
