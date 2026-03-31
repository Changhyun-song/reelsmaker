"""Frame spec planning handlers.

``handle_frame_plan``        Shot → FrameSpec[] (start / [middle] / end)
``handle_frame_regenerate``  single FrameSpec regeneration in context
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
from shared.models.frame_spec import FrameSpec
from shared.models.project import Project
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.providers import ProviderRequest, generate_validated, generate_validated_with_semantic
from shared.providers.claude_text import ClaudeTextProvider
from shared.providers.logger import log_provider_run
from shared.prompt_compiler.context_builder import build_continuity_text_block
from shared.qa.planning_guards import validate_frame_spec_semantic
from shared.schemas.contracts import FrameSpecOutput, SingleFrameSpecOutput

logger = logging.getLogger("reelsmaker.handlers.frame")

settings = get_settings()

# ── System prompts ────────────────────────────────────

_FRAME_PLAN_SYSTEM = """\
You are an expert visual director AI. You create frame specifications that are
DIRECTLY used as input for image generation AI (FLUX, Stable Diffusion, etc).
Every field must be precise, concrete, and in English.

Each shot needs: start frame + end frame (+ middle frame if shot ≥ 5 seconds).

## REQUIRED FIELDS PER FRAME

| Field | Format & Rules |
|-------|---------------|
| frame_role | "start", "middle", or "end" |
| composition | SPECIFIC technique: "Rule of thirds — subject at right-third intersection. Foreground: blurred desk items creating depth. Midground: subject in focus. Background: window with soft bokeh city lights." NOT just "rule of thirds" or "centered". Min 10 chars. |
| subject_position | Grid-based placement: "Subject occupies center-right 30% of frame, head at upper-third line, body from mid-frame to bottom edge." NOT "in the center" or "on the left". Min 5 chars. |
| camera_angle | Precise angle with degree if applicable: "eye-level, straight-on", "low-angle 20° looking up", "high-angle 45° looking down", "dutch angle 10° tilted right". Min 3 chars. |
| lens_feel | Focal length + aperture + effect: "85mm f/1.8 portrait lens, shallow DOF isolating subject from background", "24mm f/8 wide-angle, deep focus everything sharp", "50mm f/2.8 standard, natural perspective". Min 5 chars. |
| lighting | THREE-POINT description: "Key: warm 3200K from camera-left 45° above (golden hour simulation). Fill: soft cool 5600K from right at 30%, 2 stops under key. Rim/accent: thin warm edge light from behind-right creating hair highlight." NOT "nice lighting" or "well-lit". Min 10 chars. |
| mood | Emotional quality: "contemplative focus with underlying excitement" |
| action_pose | SPECIFIC physical description: "Woman leaning forward slightly, both hands on keyboard, eyes focused on screen, slight smile of concentration, shoulders relaxed." NOT "working" or "happy" or "thinking". Min 5 chars. |
| background_description | Layered description: "Immediate BG: white desk with scattered sticky notes and coffee mug. Mid BG: bookshelves with colorful spines. Far BG: large window showing twilight cityscape, warm interior reflections on glass." Min 10 chars. |
| continuity_notes | What MUST stay consistent with adjacent frames: "Same navy blazer and white shirt. Same desk setup with monitor position. Same warm-to-cool left-to-right lighting gradient. Same coffee mug position (camera-right of keyboard)." |
| forbidden_elements | Things to exclude for clean generation: "No text overlays, no watermarks, no extra hands, no face distortion, no floating objects, no inconsistent shadows." |

## START → END FRAME RELATIONSHIP (CRITICAL)
The difference between start and end frames MUST reflect the shot's camera_motion:
- static → Same composition, only subtle pose/expression change.
- slow_pan_right → Start: subject at left-third. End: subject at right-third.
  Background shifts leftward. Same subject scale.
- dolly_in → Start: wider framing. End: tighter framing. Subject larger in frame.
  Background less visible. Same angle.
- tilt_up → Start: lower portion visible. End: upper portion visible. Same lateral position.
- zoom_in → Start: more environment visible. End: subject fills more frame.
  No perspective change (unlike dolly).
- tracking → Start: subject at one position. End: subject at new position.
  Background parallax shift.

## CONTINUITY BETWEEN SHOTS
- Start frame of shot N must be compatible with end frame of shot N-1.
- If transition is "cut": lighting direction, color temperature, subject outfit must match.
- If transition is "dissolve": allow slight lighting/mood shift, keep subject consistent.

## BANNED PHRASES (will be auto-rejected if detected)
- Vague composition: "balanced", "aesthetic", "centered", "nice framing"
- Emotion-only action_pose: "happy", "focused", "excited", "thinking", "working"
  → MUST include physical body parts: "leaning forward with both hands on keyboard,
  slight smile, shoulders relaxed, head tilted 5° right"
- Vague lighting: "good lighting", "nice lighting", "well-lit", "beautiful lighting",
  "natural lighting", "studio lighting"
  → MUST use: direction (camera-left 45°) + color temperature (3200K) + role (key/fill/rim)
- Vague background: "nice background", "simple background", "clean background"

## LIGHTING STRICTNESS (CRITICAL)
- MUST describe ≥2 of: key light, fill light, rim/accent light
- MUST include direction (from where), color temperature (warm/cool or Kelvin), and
  role (key/fill/rim/accent) for each light
- Minimum 25 characters (schema enforced)
- Bad: "Warm lighting from left" → Good: "Key: warm 3200K tungsten from camera-left
  45° above at full intensity. Fill: soft cool 5600K bounced from right at 40% power.
  Rim: thin warm edge highlight from behind-right separating subject from background."

## ACTION_POSE STRICTNESS
- MUST include at least one body part reference (hands, arms, head, shoulders, etc.)
- MUST describe physical posture, not just emotional state
- Minimum 15 characters (schema enforced)
- Bad: "Looking happy" → Good: "Standing upright, right hand gesturing palm-up at
  shoulder height, left hand holding phone at waist level, chin slightly raised,
  wide genuine smile showing teeth"

## BACKGROUND_DESCRIPTION STRICTNESS
- MUST describe at least 2 depth layers (foreground + background, or near + mid + far)
- Minimum 20 characters (schema enforced)
- Bad: "Office background" → Good: "Foreground: blurred coffee mug and sticky notes.
  Mid-ground: white standing desk with dual monitors. Background: floor-to-ceiling
  window showing evening cityscape with warm interior reflections."
- Identical composition for start and end frames when camera_motion is not "static".
- Using the same subject_position for start and end when motion is pan/dolly/tracking.

Output ONLY valid JSON — no markdown fences, no commentary."""

_FRAME_REGEN_SYSTEM = """\
You are an expert visual director AI. Regenerate ONE frame spec within a shot.

Your regenerated frame must:
1. Keep the same frame_role (start/middle/end).
2. Maintain visual continuity with the other frames in this shot.
3. IMPROVE: composition specificity (rule-of-thirds/depth layers), lighting
   precision (key/fill/rim with direction and color temperature), action_pose
   concreteness (physical posture, not just emotions).
4. The composition and subject_position MUST be consistent with the shot's
   camera_motion — if it's the start frame of a dolly_in shot, the framing
   should be wider than the end frame.
5. forbidden_elements should include common AI generation artifacts.

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


def _build_prev_shot_context(prev_shot: Shot | None) -> str:
    if not prev_shot:
        return "No previous shot (this is the first shot in the scene)."
    return (
        f"Previous shot:\n"
        f"  Type: {prev_shot.shot_type} | Framing: {prev_shot.camera_framing}\n"
        f"  Subject: {prev_shot.subject or 'N/A'}\n"
        f"  Environment: {prev_shot.environment or 'N/A'}\n"
        f"  Transition out: {prev_shot.transition_out or 'cut'}"
    )


def _build_next_shot_context(next_shot: Shot | None) -> str:
    if not next_shot:
        return "No next shot (this is the last shot in the scene)."
    return (
        f"Next shot:\n"
        f"  Type: {next_shot.shot_type} | Framing: {next_shot.camera_framing}\n"
        f"  Subject: {next_shot.subject or 'N/A'}\n"
        f"  Transition in: {next_shot.transition_in or 'cut'}"
    )


# ── Handler: frame_plan ───────────────────────────────


async def handle_frame_plan(job_id: str, **params) -> dict:
    """Generate frame specs (start / [middle] / end) for a shot."""
    project_id: str = params["project_id"]
    shot_id: str = params["shot_id"]
    scene_id: str = params["scene_id"]

    async with async_session_factory() as session:
        shot = (
            await session.execute(
                select(Shot).where(Shot.id == uuid.UUID(shot_id))
            )
        ).scalar_one()

        scene = (
            await session.execute(
                select(Scene).where(Scene.id == uuid.UUID(scene_id))
            )
        ).scalar_one()

        all_shots = (
            await session.execute(
                select(Shot)
                .where(Shot.scene_id == uuid.UUID(scene_id))
                .order_by(Shot.order_index)
            )
        ).scalars().all()

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

    prev_shot: Shot | None = None
    next_shot: Shot | None = None
    for i, s in enumerate(all_shots):
        if str(s.id) == shot_id:
            if i > 0:
                prev_shot = all_shots[i - 1]
            if i < len(all_shots) - 1:
                next_shot = all_shots[i + 1]
            break

    duration = shot.duration_sec or 4
    need_middle = duration >= 5

    schema_example: dict = {
        "frames": [
            {
                "frame_role": "start",
                "composition": "...",
                "subject_position": "...",
                "camera_angle": "...",
                "lens_feel": "...",
                "lighting": "...",
                "mood": "...",
                "action_pose": "...",
                "background_description": "...",
                "continuity_notes": "...",
                "forbidden_elements": "...",
            },
        ]
    }
    if need_middle:
        schema_example["frames"].append({**schema_example["frames"][0], "frame_role": "middle"})
    schema_example["frames"].append({**schema_example["frames"][0], "frame_role": "end"})

    schema_hint = json.dumps(schema_example, ensure_ascii=False, indent=2)

    continuity_block = build_continuity_text_block(
        project.active_style_preset if project else None,
        characters,
        continuity,
    )

    camera_motion = shot.camera_movement or "static"
    motion_guide = ""
    if camera_motion in ("slow_pan_left", "pan_left"):
        motion_guide = "Start frame: subject at right portion. End frame: subject shifted to left portion. Background pans right."
    elif camera_motion in ("slow_pan_right", "pan_right"):
        motion_guide = "Start frame: subject at left portion. End frame: subject shifted to right portion. Background pans left."
    elif camera_motion in ("dolly_in", "push_in", "zoom_in"):
        motion_guide = "Start frame: wider view, more environment. End frame: tighter framing, subject larger, less background."
    elif camera_motion in ("dolly_out", "zoom_out"):
        motion_guide = "Start frame: tight on subject. End frame: wider view revealing more environment."
    elif camera_motion in ("tilt_up", "crane_up"):
        motion_guide = "Start frame: lower portion of scene. End frame: higher portion revealed."
    elif camera_motion in ("tilt_down", "crane_down"):
        motion_guide = "Start frame: upper portion. End frame: lower portion revealed."
    elif camera_motion in ("tracking_left", "tracking_right", "tracking_forward"):
        motion_guide = "Start frame: subject at initial position. End frame: subject at new position with background parallax shift."
    elif camera_motion == "static":
        motion_guide = "Start and end frame have same composition. Only subtle pose/expression change."

    continuity_section = ""
    if continuity_block:
        continuity_section = (
            f"\n## CONTINUITY CONTEXT (must be respected in every frame)\n"
            f"{continuity_block}\n"
        )

    user_prompt = (
        f"## SCENE CONTEXT\n"
        f"- Title: {scene.title or 'Untitled'}\n"
        f"- Emotional tone: {scene.emotional_tone or scene.mood or 'N/A'}\n"
        f"- Setting: {scene.setting or 'N/A'}\n"
        f"- Visual intent: {scene.visual_intent or 'N/A'}\n"
        f"{continuity_section}\n"
        f"## SHOT TO FRAME\n"
        f"- Type: {shot.shot_type} | Framing: {shot.camera_framing}\n"
        f"- Camera motion: {camera_motion}\n"
        f"- Duration: {duration}s | Strategy: {shot.asset_strategy or 'image_to_video'}\n"
        f"- Subject: {shot.subject or 'N/A'}\n"
        f"- Environment: {shot.environment or 'N/A'}\n"
        f"- Emotion: {shot.emotion or 'N/A'}\n"
        f"- Full description: {shot.description or 'N/A'}\n"
        f"- Transition in: {shot.transition_in or 'cut'} | out: {shot.transition_out or 'cut'}\n\n"
        f"## CAMERA MOTION → FRAME RELATIONSHIP\n"
        f"{motion_guide}\n\n"
        f"## ADJACENT SHOTS (for continuity)\n"
        f"{_build_prev_shot_context(prev_shot)}\n\n"
        f"{_build_next_shot_context(next_shot)}\n\n"
        f"## TASK\n"
        f"Generate {'start + middle + end' if need_middle else 'start + end'} frame specs.\n"
        f"- composition must be ≥10 chars with specific technique\n"
        f"- lighting must describe key/fill/rim with direction and temperature\n"
        f"- action_pose must be physical description, not just emotion\n"
        f"- start ↔ end frames must differ according to camera motion above\n"
        f"- Respect all CONTINUITY CONTEXT rules (style, character, lighting, color)\n"
        f"- Include continuity_notes referencing locked elements\n\n"
        f"Output JSON matching:\n{schema_hint}"
    )

    provider = _get_provider()
    request = ProviderRequest(
        system_prompt=_FRAME_PLAN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.6,
        max_tokens=4096,
    )

    await _update_job_progress(job_id, 10)

    try:
        response, result = await generate_validated_with_semantic(
            provider, request, FrameSpecOutput,
            semantic_guard=validate_frame_spec_semantic,
            max_attempts=2, max_semantic_retries=1,
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="frame_plan",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="frame_plan",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 60)

    roles_present = {f.frame_role for f in result.frames}
    if "start" not in roles_present or "end" not in roles_present:
        raise ValueError(
            f"AI output missing required roles. Got: {roles_present}, need start+end"
        )

    role_order = {"start": 0, "middle": 1, "end": 2}
    sorted_frames = sorted(result.frames, key=lambda f: role_order.get(f.frame_role, 1))

    duration_per_frame = int((duration * 1000) / len(sorted_frames))

    async with async_session_factory() as session:
        await session.execute(
            delete(FrameSpec).where(FrameSpec.shot_id == uuid.UUID(shot_id))
        )

        for idx, item in enumerate(sorted_frames):
            spec = FrameSpec(
                shot_id=uuid.UUID(shot_id),
                order_index=idx,
                frame_role=item.frame_role,
                composition=item.composition,
                subject_position=item.subject_position,
                camera_angle=item.camera_angle,
                lens_feel=item.lens_feel,
                lighting=item.lighting,
                mood=item.mood,
                action_pose=item.action_pose,
                background_description=item.background_description,
                continuity_notes=item.continuity_notes,
                forbidden_elements=item.forbidden_elements,
                duration_ms=duration_per_frame,
                status="drafted",
                plan_json=item.model_dump(),
            )
            session.add(spec)

        await session.commit()

    await _update_job_progress(job_id, 100)

    return {
        "shot_id": shot_id,
        "frames_count": len(sorted_frames),
        "roles": [f.frame_role for f in sorted_frames],
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }


# ── Handler: frame_regenerate ─────────────────────────


async def handle_frame_regenerate(job_id: str, **params) -> dict:
    """Regenerate a single frame spec in context."""
    project_id: str = params["project_id"]
    frame_id: str = params["frame_id"]
    shot_id: str = params["shot_id"]

    async with async_session_factory() as session:
        target_frame = (
            await session.execute(
                select(FrameSpec).where(FrameSpec.id == uuid.UUID(frame_id))
            )
        ).scalar_one()

        all_frames = (
            await session.execute(
                select(FrameSpec)
                .where(FrameSpec.shot_id == uuid.UUID(shot_id))
                .order_by(FrameSpec.order_index)
            )
        ).scalars().all()

        shot = (
            await session.execute(
                select(Shot).where(Shot.id == uuid.UUID(shot_id))
            )
        ).scalar_one()

    context_lines: list[str] = []
    for f in all_frames:
        marker = " <<<< REGENERATE THIS FRAME" if str(f.id) == frame_id else ""
        context_lines.append(
            f"[{f.frame_role or 'frame'} (idx={f.order_index})]{marker}\n"
            f"  Composition: {f.composition or 'N/A'}\n"
            f"  Subject pos: {f.subject_position or 'N/A'}\n"
            f"  Camera angle: {f.camera_angle or 'N/A'}\n"
            f"  Lighting: {f.lighting or 'N/A'}\n"
            f"  Mood: {f.mood or 'N/A'}\n"
            f"  Action/Pose: {f.action_pose or 'N/A'}"
        )

    schema_hint = json.dumps(
        {
            "composition": "...",
            "subject_position": "...",
            "camera_angle": "...",
            "lens_feel": "...",
            "lighting": "...",
            "mood": "...",
            "action_pose": "...",
            "background_description": "...",
            "continuity_notes": "...",
            "forbidden_elements": "...",
        },
        ensure_ascii=False,
    )

    user_prompt = (
        f"Shot: {shot.shot_type} | {shot.camera_framing} | {shot.camera_movement}\n"
        f"Subject: {shot.subject or 'N/A'}\n"
        f"Environment: {shot.environment or 'N/A'}\n\n"
        f"=== ALL FRAMES ===\n"
        + "\n\n".join(context_lines)
        + f"\n=== END ===\n\n"
        f"Regenerate the frame marked with <<<< REGENERATE THIS FRAME.\n"
        f"Its role is '{target_frame.frame_role or 'start'}'.\n"
        f"Output JSON matching:\n{schema_hint}"
    )

    provider = _get_provider()
    request = ProviderRequest(
        system_prompt=_FRAME_REGEN_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=2048,
    )

    await _update_job_progress(job_id, 20)

    try:
        response, result = await generate_validated(
            provider, request, SingleFrameSpecOutput, max_attempts=3
        )
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="frame_regenerate",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="frame_regenerate",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 70)

    async with async_session_factory() as session:
        frame = (
            await session.execute(
                select(FrameSpec).where(FrameSpec.id == uuid.UUID(frame_id))
            )
        ).scalar_one()

        frame.composition = result.composition
        frame.subject_position = result.subject_position
        frame.camera_angle = result.camera_angle
        frame.lens_feel = result.lens_feel
        frame.lighting = result.lighting
        frame.mood = result.mood
        frame.action_pose = result.action_pose
        frame.background_description = result.background_description
        frame.continuity_notes = result.continuity_notes
        frame.forbidden_elements = result.forbidden_elements
        frame.status = "drafted"
        frame.plan_json = result.model_dump()

        await session.commit()

    await _update_job_progress(job_id, 100)

    return {
        "frame_id": frame_id,
        "frame_role": target_frame.frame_role,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }
