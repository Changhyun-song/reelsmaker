"""Script planning handlers — AI-integrated handlers for script lifecycle.

``handle_script_generate``  user inputs → structured script plan (ScriptPlanOutput)
``handle_script_structure`` raw narration → Scene → Shot → Frame hierarchy
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select

from shared.config import get_settings
from shared.database import async_session_factory
from shared.models.frame_spec import FrameSpec
from shared.models.scene import Scene
from shared.models.script_version import ScriptVersion
from shared.models.shot import Shot
from shared.providers import ProviderRequest, generate_validated, generate_validated_with_semantic
from shared.providers.claude_text import ClaudeTextProvider
from shared.providers.logger import log_provider_run
from shared.qa.planning_guards import validate_script_plan_semantic
from shared.schemas.contracts import ScriptPlanOutput, ScriptStructureOutput

logger = logging.getLogger("reelsmaker.handlers.script")

settings = get_settings()

# ── System prompts ────────────────────────────────────

_PLAN_SYSTEM = """\
You are an elite short-form video scriptwriter. You write scripts optimized for
viewer retention in 15-120 second videos (YouTube Shorts, Reels, TikTok).

Given user inputs, create a structured script plan.

## OUTPUT FIELDS

1. **title** — compelling, curiosity-driven title (≤12 words)
2. **summary** — one-paragraph elevator pitch explaining WHY a viewer would watch
3. **hook** — the exact first sentence spoken in the first 3 seconds.
   MUST be one of: a surprising statistic, a provocative question, a bold
   counter-intuitive claim, or a "what if" scenario. Never a generic intro.
4. **narrative_flow** — 3-7 key story beats as bullet points
5. **sections** — logical sections covering the ENTIRE video:
   - title: section label
   - description: what this section achieves (≥5 words)
   - narration: the EXACT spoken words for this section
   - visual_notes: what appears on screen, described with enough detail for a
     cinematographer. Use format: "[Shot type] Subject doing action in environment.
     Lighting: X. Camera: Y." Do NOT write vague notes like "show the product" or
     "relevant visuals".
   - duration_sec: realistic estimate
6. **ending_cta** — specific call-to-action (not "like and subscribe")
7. **narration_draft** — all sections' narration joined with natural transitions.
   Must sound natural when read aloud at normal speed.
8. **estimated_duration_sec** — total duration

## PACING RULES
- Korean: ~3.5 syllables/sec → ~150 words/min
- English: ~2.5 words/sec → ~130 words/min
- Section durations must sum to ±15% of requested total duration
- Hook ≤ 3 seconds of narration

## BANNED PATTERNS (will be rejected if used)
- Generic openers: "오늘은", "안녕하세요", "Hi everyone", "In this video",
  "welcome to", "hey guys", "여러분"
- Filler transitions: "자, 그럼", "다음으로", "Now let's move on"
- Vague visual notes: "relevant image", "show example", "적절한 영상",
  "관련 이미지", "적절한 이미지", "nice visuals", "good visuals"
- Vague descriptors anywhere: "beautiful shot", "nice background", "amazing visual",
  "stunning", "gorgeous", "aesthetic"
- Placeholder text in any field

## VISUAL_NOTES STRICTNESS
- MUST be ≥20 characters
- MUST follow format: "[Shot type] Subject doing action in environment.
  Lighting: X. Camera: Y."
- MUST include ALL of: shot type in brackets, specific subject, specific lighting
  direction/quality, camera movement or angle
- Bad: "Show the app interface" → Good: "[Close-up] Smartphone screen displaying
  Notion app in dark mode, user's hands scrolling. Lighting: soft blue screen glow
  illuminating face from below. Camera: slow dolly in over 3 seconds."

## Output ONLY valid JSON — no markdown fences, no commentary."""

_STRUCTURE_SYSTEM = """\
You are a professional screenplay structuring AI for short-form video production.
Decompose a raw script into: Scene → Shot → Frame hierarchy.

## SCENE RULES
- Each scene = one coherent location/setting with consistent emotional tone.
- setting must be a concrete location (English), not abstract.
- mood is 1-3 emotion keywords.

## SHOT RULES
- Each shot = 2-8 seconds of continuous camera.
- shot_type: establishing, close_up, medium, wide, detail, pov, insert, reaction.
- camera_movement: static, pan_left, pan_right, zoom_in, zoom_out, tracking,
  tilt_up, tilt_down, dolly_in, dolly_out, handheld, crane_up, orbit_left.
- description must describe what is VISIBLE, not story beats.

## FRAME RULES
- visual_prompt MUST be in English (image AI requirement).
- visual_prompt must be a standalone image generation prompt with subject, action,
  environment, lighting, camera angle, style — minimum 15 words.
- negative_prompt: list unwanted elements in English (e.g. "cartoon, blurry, text").
- duration_ms within a shot must sum to ≈ shot duration_sec × 1000.

## BANNED
- Vague visual_prompts like "beautiful scene" or "the character".
- Setting descriptions like "somewhere nice" or "a place".

Output ONLY the JSON object — no markdown fences, no explanation."""


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


# ── Handler: script_generate (Script Plan) ────────────


async def handle_script_generate(job_id: str, **params) -> dict:
    """Generate a structured script plan from user inputs."""
    project_id: str = params["project_id"]
    topic: str = params.get("topic", "")
    target_audience: str = params.get("target_audience", "")
    tone: str = params.get("tone", "")
    duration_sec: int = params.get("duration_sec", 60)
    video_format: str = params.get("format", "youtube_short")
    language: str = params.get("language", "ko")
    constraints: str = params.get("constraints", "")

    input_params = {
        "topic": topic,
        "target_audience": target_audience,
        "tone": tone,
        "duration_sec": duration_sec,
        "format": video_format,
        "language": language,
        "constraints": constraints,
    }

    provider = _get_provider()

    user_prompt = (
        f"## INPUT\n"
        f"- Topic: {topic}\n"
        f"- Target audience: {target_audience or 'general'}\n"
        f"- Tone/mood: {tone or 'engaging, informative'}\n"
        f"- Target duration: {duration_sec} seconds\n"
        f"- Format: {video_format}\n"
        f"- Language: {language}\n"
    )
    if constraints:
        user_prompt += f"- Additional constraints: {constraints}\n"

    user_prompt += (
        f"\n## EXPECTED OUTPUT\n"
        f"Return a JSON object with these exact keys:\n"
        f"  title (string), summary (string), hook (string ≥5 chars),\n"
        f"  narrative_flow (array of strings, ≥2 items),\n"
        f"  sections (array, ≥2 items, each with: title, description ≥5 chars,\n"
        f"    narration ≥5 chars, visual_notes ≥5 chars, duration_sec),\n"
        f"  ending_cta (string ≥5 chars),\n"
        f"  narration_draft (string ≥20 chars — the full narration),\n"
        f"  estimated_duration_sec (number)\n"
        f"\n## EXAMPLE visual_notes FORMAT\n"
        f'  "[Close-up] Smartphone screen showing Notion app interface, dark mode. '
        f'Lighting: soft screen glow on face. Camera: slow dolly in."\n'
        f'  NOT: "show the app" or "관련 이미지"\n'
    )

    request = ProviderRequest(
        system_prompt=_PLAN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.8,
        max_tokens=4096,
    )

    await _update_job_progress(job_id, 10)

    try:
        response, result = await generate_validated_with_semantic(
            provider, request, ScriptPlanOutput,
            semantic_guard=validate_script_plan_semantic,
            max_attempts=3, max_semantic_retries=2,
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="script_generate",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="script_generate",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 70)

    plan_data = result.model_dump()

    async with async_session_factory() as session:
        existing = await session.execute(
            select(ScriptVersion)
            .where(ScriptVersion.project_id == uuid.UUID(project_id))
            .order_by(ScriptVersion.version.desc())
            .limit(1)
        )
        prev = existing.scalar_one_or_none()
        next_version = (prev.version + 1) if prev else 1

        sv = ScriptVersion(
            project_id=uuid.UUID(project_id),
            version=next_version,
            raw_text=result.narration_draft,
            status="draft",
            parent_version_id=prev.id if prev else None,
            input_params=input_params,
            plan_json=plan_data,
        )
        session.add(sv)
        await session.commit()
        await session.refresh(sv)
        script_version_id = str(sv.id)

    await _update_job_progress(job_id, 100)

    return {
        "script_version_id": script_version_id,
        "version": next_version,
        "title": result.title,
        "summary": result.summary,
        "sections_count": len(result.sections),
        "estimated_duration_sec": result.estimated_duration_sec,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }


# ── Handler: script_structure ─────────────────────────


async def handle_script_structure(job_id: str, **params) -> dict:
    """Structure a ScriptVersion's raw_text into Scene → Shot → Frame."""
    script_version_id: str = params["script_version_id"]

    async with async_session_factory() as session:
        sv = (
            await session.execute(
                select(ScriptVersion).where(
                    ScriptVersion.id == uuid.UUID(script_version_id)
                )
            )
        ).scalar_one()
        project_id = sv.project_id
        raw_text = sv.raw_text or ""

    if not raw_text.strip():
        raise ValueError("ScriptVersion has no raw_text to structure")

    provider = _get_provider()

    schema_hint = (
        '{"scenes": [{"title": "...", "description": "...", "setting": "...", '
        '"mood": "...", "duration_estimate_sec": N, "shots": [{"shot_type": "...", '
        '"description": "...", "camera_movement": "...", "duration_sec": N, '
        '"frames": [{"visual_prompt": "...", "negative_prompt": "...", '
        '"dialogue": "...", "dialogue_character": "...", "duration_ms": N, '
        '"transition_type": "..."}]}]}]}'
    )

    user_prompt = (
        f"Here is the raw script to structure:\n\n{raw_text}\n\n"
        f"Break this script into scenes, shots, and frames.\n"
        f"Output JSON matching this schema:\n{schema_hint}"
    )

    request = ProviderRequest(
        system_prompt=_STRUCTURE_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=8192,
    )

    await _update_job_progress(job_id, 10)

    try:
        response, result = await generate_validated(
            provider, request, ScriptStructureOutput, max_attempts=3
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="script_structure",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="script_structure",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 50)

    scenes_count = len(result.scenes)
    total_shots = 0
    total_frames = 0

    async with async_session_factory() as session:
        for i, scene_plan in enumerate(result.scenes):
            scene = Scene(
                script_version_id=uuid.UUID(script_version_id),
                order_index=i,
                title=scene_plan.title,
                description=scene_plan.description,
                setting=scene_plan.setting,
                mood=scene_plan.mood,
                duration_estimate_sec=scene_plan.duration_estimate_sec,
                status="ready",
            )
            session.add(scene)
            await session.flush()

            for j, shot_plan in enumerate(scene_plan.shots):
                total_shots += 1
                shot = Shot(
                    scene_id=scene.id,
                    order_index=j,
                    shot_type=shot_plan.shot_type,
                    description=shot_plan.description,
                    camera_movement=shot_plan.camera_movement,
                    duration_sec=shot_plan.duration_sec,
                    status="ready",
                )
                session.add(shot)
                await session.flush()

                for k, frame_plan in enumerate(shot_plan.frames):
                    total_frames += 1
                    frame = FrameSpec(
                        shot_id=shot.id,
                        order_index=k,
                        visual_prompt=frame_plan.visual_prompt,
                        negative_prompt=frame_plan.negative_prompt,
                        dialogue=frame_plan.dialogue,
                        duration_ms=frame_plan.duration_ms,
                        transition_type=frame_plan.transition_type,
                        status="prompts_ready",
                    )
                    session.add(frame)

            progress = 50 + int((i + 1) / scenes_count * 40)
            await _update_job_progress(job_id, progress)

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
        "scenes": scenes_count,
        "shots": total_shots,
        "frames": total_frames,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }
