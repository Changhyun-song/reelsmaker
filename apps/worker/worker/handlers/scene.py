"""Scene planning handlers.

``handle_scene_plan``        ScriptVersion → Scene[] breakdown
``handle_scene_regenerate``  single Scene regeneration in context
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select, delete

from shared.config import get_settings
from shared.database import async_session_factory
from shared.models.scene import Scene
from shared.models.script_version import ScriptVersion
from shared.providers import ProviderRequest, generate_validated, generate_validated_with_semantic
from shared.providers.claude_text import ClaudeTextProvider
from shared.providers.logger import log_provider_run
from shared.qa.planning_guards import validate_scene_breakdown_semantic
from shared.schemas.contracts import SceneBreakdownOutput, SingleSceneOutput

logger = logging.getLogger("reelsmaker.handlers.scene")

settings = get_settings()

# ── System prompts ────────────────────────────────────

_SCENE_PLAN_SYSTEM = """\
You are an expert video director AI. Break a narration script into individual
scenes — each a coherent narrative unit with one location, one emotional register,
and one clear purpose.

## REQUIRED FIELDS PER SCENE

| Field | Rules |
|-------|-------|
| scene_index | 0-based sequential |
| title | Short, descriptive (≤8 words) |
| purpose | Narrative function: "hook viewer with surprising stat", "build tension before reveal", "resolve with practical takeaway". NOT vague like "transition" or "middle part". |
| summary | 1-2 sentence overview (≥10 chars) |
| narration_text | Exact voiceover text for this scene, in the script's language. Concatenation of all scenes must reproduce the FULL original script — no skipping, no paraphrasing. |
| setting | Concrete visual location in English for image AI: "modern minimalist home office, white desk, single monitor, afternoon sunlight through blinds". NOT "an office" or "a nice place". |
| mood | 1-3 emotion keywords: "curious, slightly anxious" |
| emotional_tone | Detailed direction for visuals + music: "Start with wonder and gentle awe, shift to focused determination by scene end. Background music: soft ambient piano, building." |
| visual_intent | What the viewer SEES, in English, concrete enough for an image generation AI. Describe dominant visual elements, color temperature, movement type. Example: "Close shots of hands typing on keyboard, interspersed with floating digital interface mockups, cool blue-teal palette, gentle zoom movements." |
| transition_hint | How to transition to the NEXT scene: "dissolve", "cut", "fade_to_black", "smash_cut", "none" (last scene) |
| estimated_duration_sec | Realistic duration (2-300s) |

Also output **total_duration_sec** (sum of all scene durations).

## CONTINUITY RULES
- Adjacent scenes must not have jarring mood jumps. If scene N is "calm" and scene
  N+1 is "intense", there must be a transitional beat in the narration.
- Color temperature should shift gradually: don't jump from warm golden to cold blue
  without a visual_intent that explains the transition.
- The last scene's transition_hint must be "none".

## DURATION RULES
- total_duration_sec must be within ±20% of the target duration.
- For videos ≤60s: 3-6 scenes, each 5-20s.
- For videos 60-180s: 4-10 scenes, each 10-30s.

## BANNED PHRASES (will be auto-rejected if detected)
- Vague purpose: "continue the story", "transition", "middle part"
- Generic setting: "an office", "a room", "somewhere", "nice place", "a place",
  "a studio", "a space", "relevant location", "indoors", "outdoors"
- Vague visual_intent: "beautiful scene", "nice background", "stunning visuals",
  "aesthetic", "gorgeous", "amazing visual"
- visual_intent that just restates the narration in English without visual specifics

## SETTING STRICTNESS
- MUST include: materials/textures, key objects (≥2), lighting condition, spatial feel
- Bad: "an office" → Good: "modern open-plan office with exposed concrete ceiling,
  standing desks with dual monitors, floor-to-ceiling windows showing rainy cityscape,
  overhead pendant Edison bulbs casting warm pools of light"

## VISUAL_INTENT STRICTNESS
- MUST include: dominant color temperature/palette AND specific camera style AND
  at least 2 concrete visual objects or actions
- Bad: "Show the concept visually" → Good: "Tight close-ups of fingers tapping phone
  screen alternating with floating UI mockup overlays, cool blue-teal palette with
  warm amber accent highlights, smooth tracking movements at 24fps"
- Scenes shorter than 3s or longer than 60s for short-form content.

Output ONLY valid JSON — no markdown fences, no commentary."""

_SCENE_REGEN_SYSTEM = """\
You are an expert video director AI. Regenerate ONE scene within a larger script.

Your regenerated scene must:
1. Keep the same narration_text (exact same words, you can only adjust punctuation).
2. Keep the same approximate duration (±2 seconds).
3. IMPROVE: setting specificity, visual_intent concreteness, emotional_tone depth.
4. Maintain smooth mood/color continuity with the scenes before and after it.
5. Ensure the transition_hint creates a natural bridge to the next scene.

Avoid: vague visual_intent, placeholder setting, purpose that says "continue".

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


# ── Handler: scene_plan ───────────────────────────────


async def handle_scene_plan(job_id: str, **params) -> dict:
    """Break a ScriptVersion into scenes."""
    project_id: str = params["project_id"]
    script_version_id: str = params["script_version_id"]

    async with async_session_factory() as session:
        sv = (
            await session.execute(
                select(ScriptVersion).where(
                    ScriptVersion.id == uuid.UUID(script_version_id)
                )
            )
        ).scalar_one()
        raw_text = sv.raw_text or ""
        plan_json = sv.plan_json or {}

    if not raw_text.strip():
        raise ValueError("ScriptVersion has no narration text to break into scenes")

    target_duration = plan_json.get("estimated_duration_sec", 60)
    language = (sv.input_params or {}).get("language", "ko")

    provider = _get_provider()

    schema_hint = json.dumps(
        {
            "scenes": [
                {
                    "scene_index": 0,
                    "title": "...",
                    "purpose": "...",
                    "summary": "...",
                    "narration_text": "...",
                    "setting": "...",
                    "mood": "...",
                    "emotional_tone": "...",
                    "visual_intent": "...",
                    "transition_hint": "...",
                    "estimated_duration_sec": 0,
                }
            ],
            "total_duration_sec": 0,
        },
        ensure_ascii=False,
    )

    user_prompt = (
        f"## INPUT\n"
        f"- Script language: {language}\n"
        f"- Target total duration: {target_duration} seconds\n"
        f"- Video type: short-form vertical video\n\n"
        f"## FULL NARRATION (every word must appear in exactly one scene's narration_text)\n"
        f"{raw_text}\n\n"
        f"## TASK\n"
        f"Break this narration into scenes. Each scene's narration_text must contain\n"
        f"the exact original words (no rewriting). All scenes' narration_text\n"
        f"concatenated = the full narration above.\n\n"
        f"Output JSON matching:\n{schema_hint}"
    )

    request = ProviderRequest(
        system_prompt=_SCENE_PLAN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.6,
        max_tokens=8192,
    )

    await _update_job_progress(job_id, 10)

    try:
        response, result = await generate_validated_with_semantic(
            provider, request, SceneBreakdownOutput,
            semantic_guard=validate_scene_breakdown_semantic,
            max_attempts=3, max_semantic_retries=2,
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="scene_plan",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="scene_plan",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 60)

    # Duration validation
    drift = abs(result.total_duration_sec - target_duration) / max(target_duration, 1)
    duration_warning = None
    if drift > 0.2:
        duration_warning = (
            f"Total scene duration {result.total_duration_sec:.1f}s "
            f"deviates {drift:.0%} from target {target_duration}s"
        )
        logger.warning("scene_plan %s: %s", job_id, duration_warning)

    # Delete existing scenes for this script version, then insert new ones
    async with async_session_factory() as session:
        await session.execute(
            delete(Scene).where(Scene.script_version_id == uuid.UUID(script_version_id))
        )

        for item in result.scenes:
            scene = Scene(
                script_version_id=uuid.UUID(script_version_id),
                order_index=item.scene_index,
                title=item.title,
                description=item.summary,
                setting=item.setting,
                mood=item.mood,
                duration_estimate_sec=item.estimated_duration_sec,
                status="drafted",
                purpose=item.purpose,
                narration_text=item.narration_text,
                emotional_tone=item.emotional_tone,
                visual_intent=item.visual_intent,
                transition_hint=item.transition_hint,
                plan_json=item.model_dump(),
            )
            session.add(scene)

        sv_obj = (
            await session.execute(
                select(ScriptVersion).where(
                    ScriptVersion.id == uuid.UUID(script_version_id)
                )
            )
        ).scalar_one()
        sv_obj.status = "structured"

        await session.commit()

    await _update_job_progress(job_id, 100)

    return {
        "script_version_id": script_version_id,
        "scenes_count": len(result.scenes),
        "total_duration_sec": result.total_duration_sec,
        "target_duration_sec": target_duration,
        "duration_warning": duration_warning,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }


# ── Handler: scene_regenerate ─────────────────────────


async def handle_scene_regenerate(job_id: str, **params) -> dict:
    """Regenerate a single scene in context."""
    project_id: str = params["project_id"]
    scene_id: str = params["scene_id"]
    script_version_id: str = params["script_version_id"]

    async with async_session_factory() as session:
        target_scene = (
            await session.execute(select(Scene).where(Scene.id == uuid.UUID(scene_id)))
        ).scalar_one()

        all_scenes = (
            await session.execute(
                select(Scene)
                .where(Scene.script_version_id == uuid.UUID(script_version_id))
                .order_by(Scene.order_index)
            )
        ).scalars().all()

        sv = (
            await session.execute(
                select(ScriptVersion).where(
                    ScriptVersion.id == uuid.UUID(script_version_id)
                )
            )
        ).scalar_one()

    language = (sv.input_params or {}).get("language", "ko")

    # Build context: show all scenes with the target marked
    context_lines: list[str] = []
    for s in all_scenes:
        marker = " <<<< REGENERATE THIS SCENE" if str(s.id) == scene_id else ""
        context_lines.append(
            f"[Scene {s.order_index}] {s.title}{marker}\n"
            f"  Purpose: {s.purpose or 'N/A'}\n"
            f"  Narration: {s.narration_text or 'N/A'}\n"
            f"  Duration: {s.duration_estimate_sec or 0}s\n"
            f"  Mood: {s.mood or 'N/A'} | Tone: {s.emotional_tone or 'N/A'}"
        )

    schema_hint = json.dumps(
        {
            "title": "...",
            "purpose": "...",
            "summary": "...",
            "narration_text": "...",
            "setting": "...",
            "mood": "...",
            "emotional_tone": "...",
            "visual_intent": "...",
            "transition_hint": "...",
            "estimated_duration_sec": 0,
        },
        ensure_ascii=False,
    )

    user_prompt = (
        f"Language: {language}\n\n"
        f"=== ALL SCENES (context) ===\n"
        + "\n\n".join(context_lines)
        + f"\n=== END ===\n\n"
        f"Regenerate the scene marked with <<<< REGENERATE THIS SCENE.\n"
        f"Keep the same approximate duration ({target_scene.duration_estimate_sec or 10}s) "
        f"and maintain continuity with surrounding scenes.\n"
        f"Output JSON matching:\n{schema_hint}"
    )

    provider = _get_provider()
    request = ProviderRequest(
        system_prompt=_SCENE_REGEN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=2048,
    )

    await _update_job_progress(job_id, 20)

    try:
        response, result = await generate_validated(
            provider, request, SingleSceneOutput, max_attempts=3
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="scene_regenerate",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="scene_regenerate",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 70)

    # Update scene in-place
    async with async_session_factory() as session:
        scene = (
            await session.execute(select(Scene).where(Scene.id == uuid.UUID(scene_id)))
        ).scalar_one()

        scene.title = result.title
        scene.description = result.summary
        scene.purpose = result.purpose
        scene.narration_text = result.narration_text
        scene.setting = result.setting
        scene.mood = result.mood
        scene.emotional_tone = result.emotional_tone
        scene.visual_intent = result.visual_intent
        scene.transition_hint = result.transition_hint
        scene.duration_estimate_sec = result.estimated_duration_sec
        scene.status = "drafted"
        scene.plan_json = result.model_dump()

        await session.commit()

    await _update_job_progress(job_id, 100)

    return {
        "scene_id": scene_id,
        "title": result.title,
        "estimated_duration_sec": result.estimated_duration_sec,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }
