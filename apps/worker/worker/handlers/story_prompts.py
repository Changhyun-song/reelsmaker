"""Story-aware visual prompt generation.

Generates rich, detailed visual prompts for ALL frames at once,
considering the full story narrative, scene transitions, and visual continuity.
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select

from shared.config import get_settings
from shared.database import async_session_factory
from shared.models.frame_spec import FrameSpec
from shared.models.project import Project
from shared.models.scene import Scene
from shared.models.script_version import ScriptVersion
from shared.models.shot import Shot
from shared.providers import ProviderRequest
from shared.providers.claude_text import ClaudeTextProvider
from shared.providers.logger import log_provider_run

logger = logging.getLogger("reelsmaker.handlers.story_prompts")

settings = get_settings()

_SYSTEM_PROMPT = """\
You are a world-class visual director creating image generation prompts for a short-form video.

You will receive the ENTIRE story (all scenes, shots, frames) and must generate a detailed
visual prompt for EACH frame. Your prompts will be fed directly to an AI image generator
(Gemini Imagen, FLUX, etc).

## CRITICAL RULES

### 1. NARRATIVE COHERENCE
- Every prompt must serve the story being told
- Characters must look consistent across ALL frames (same clothes, hair, features)
- Environment must evolve logically (if it's sunset in frame 1, it can't be noon in frame 5)
- Props and objects that appear must persist or disappear logically

### 2. VISUAL CONTINUITY  
- Adjacent frames (especially within the same shot) must feel like they belong together
- Color palette must be consistent across the entire video
- Lighting direction must be physically consistent within a scene
- Camera perspective must match the shot description

### 3. PROMPT QUALITY
Each prompt must include ALL of these elements in a SINGLE descriptive paragraph:
- Subject description (who/what, appearance, pose, expression)
- Action (what is happening)
- Environment (where, background layers)
- Lighting (direction, color temperature, quality)
- Camera angle and framing
- Mood/atmosphere
- Art style consistency marker (e.g., "cinematic 4K", "anime style", "watercolor illustration")

### 4. NEGATIVE PROMPT
Provide one shared negative prompt for the entire batch that covers:
- Common AI artifacts (extra fingers, deformed faces, etc.)
- Unwanted elements (text overlays, watermarks, logos)
- Style inconsistencies to avoid

### 5. FORMAT
Output JSON:
{
  "frame_prompts": [
    {
      "frame_id": "<uuid>",
      "visual_prompt": "<detailed prompt, 100-250 words>",
      "style_anchor": "<3-5 word style consistency tag>"
    }
  ],
  "shared_negative_prompt": "<negative prompt>",
  "style_summary": "<1 sentence describing the overall visual style>"
}

Write ALL prompts in English. Be specific, concrete, and vivid.
Avoid vague words like "beautiful", "nice", "amazing".
Every prompt must be self-contained (the image generator sees only ONE prompt at a time)."""


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


async def handle_story_prompts(job_id: str, **params) -> dict:
    """Generate visual prompts for all frames based on the full story context."""
    project_id: str = params["project_id"]
    script_version_id: str = params["script_version_id"]

    async with async_session_factory() as session:
        project = (
            await session.execute(
                select(Project).where(Project.id == uuid.UUID(project_id))
            )
        ).scalar_one()

        script = (
            await session.execute(
                select(ScriptVersion).where(
                    ScriptVersion.id == uuid.UUID(script_version_id)
                )
            )
        ).scalar_one()

        scenes = list(
            (
                await session.execute(
                    select(Scene)
                    .where(Scene.script_version_id == uuid.UUID(script_version_id))
                    .order_by(Scene.order_index)
                )
            ).scalars().all()
        )

        all_shots: list[Shot] = []
        all_frames: list[FrameSpec] = []

        for scene in scenes:
            shots = list(
                (
                    await session.execute(
                        select(Shot)
                        .where(Shot.scene_id == scene.id)
                        .order_by(Shot.order_index)
                    )
                ).scalars().all()
            )
            all_shots.extend(shots)

            for shot in shots:
                frames = list(
                    (
                        await session.execute(
                            select(FrameSpec)
                            .where(FrameSpec.shot_id == shot.id)
                            .order_by(FrameSpec.order_index)
                        )
                    ).scalars().all()
                )
                all_frames.extend(frames)

    if not all_frames:
        return {"error": "No frames found", "frames_updated": 0}

    await _update_job_progress(job_id, 10)

    # Build comprehensive story context
    story_parts: list[str] = []
    story_parts.append(f"## PROJECT: {project.title or 'Untitled'}")
    story_parts.append(f"Style: {project.style or 'cinematic'}")
    story_parts.append(f"Duration: ~{project.target_duration_sec or 30}s")
    story_parts.append(f"Resolution: {project.width or 1080}x{project.height or 1920}")
    story_parts.append("")

    # Inject Continuity Bible if available
    bible = (project.settings or {}).get("bible")
    if bible and any(bible.values()):
        story_parts.append("## CONTINUITY BIBLE (must be respected in ALL frames)")
        for key, label in [
            ("main_subject_identity", "Main Subject Identity"),
            ("character_visual_rules", "Character Visual Rules"),
            ("wardrobe_rules", "Wardrobe Rules"),
            ("palette_rules", "Color Palette Rules"),
            ("lighting_rules", "Lighting Rules"),
            ("lens_rules", "Lens / Camera Rules"),
            ("environment_consistency_rules", "Environment Consistency"),
            ("forbidden_drift_rules", "Forbidden Drift (NEVER change these)"),
        ]:
            val = bible.get(key, "")
            if val:
                story_parts.append(f"- {label}: {val}")
        story_parts.append("")

    if script.narration_draft:
        story_parts.append(f"## FULL NARRATION\n{script.narration_draft}")
        story_parts.append("")

    frame_index_map: dict[str, int] = {}
    global_frame_idx = 0

    for si, scene in enumerate(scenes):
        scene_shots = [s for s in all_shots if s.scene_id == scene.id]
        story_parts.append(f"### SCENE {si + 1}: {scene.title or 'Untitled'}")
        if scene.description:
            story_parts.append(f"Description: {scene.description}")
        if scene.narration_text:
            story_parts.append(f'Narration: "{scene.narration_text}"')
        story_parts.append(f"Mood: {scene.mood or scene.emotional_tone or 'N/A'}")
        story_parts.append(f"Setting: {scene.setting or 'N/A'}")
        story_parts.append("")

        for shi, shot in enumerate(scene_shots):
            shot_frames = [f for f in all_frames if f.shot_id == shot.id]
            story_parts.append(
                f"  Shot {si+1}-{shi+1}: {shot.shot_type or 'standard'} | "
                f"{shot.camera_framing or 'medium'} | "
                f"motion: {shot.camera_movement or 'static'} | "
                f"{shot.duration_sec or 4}s"
            )
            if shot.subject:
                story_parts.append(f"    Subject: {shot.subject}")
            if shot.environment:
                story_parts.append(f"    Environment: {shot.environment}")
            if shot.description:
                story_parts.append(f"    Description: {shot.description}")

            for fi, frame in enumerate(shot_frames):
                frame_id_str = str(frame.id)
                frame_index_map[frame_id_str] = global_frame_idx
                story_parts.append(
                    f"    → Frame {global_frame_idx + 1} (id: {frame_id_str}) "
                    f"[{frame.frame_role}]: "
                    f"composition={frame.composition or 'N/A'}, "
                    f"camera={frame.camera_angle or 'N/A'}, "
                    f"action={frame.action_pose or 'N/A'}, "
                    f"lighting={frame.lighting or 'N/A'}"
                )
                global_frame_idx += 1

            story_parts.append("")

    story_context = "\n".join(story_parts)

    user_prompt = (
        f"{story_context}\n\n"
        f"## TASK\n"
        f"Generate a detailed visual prompt for each of the {len(all_frames)} frames above.\n"
        f"Remember:\n"
        f"- Characters must look IDENTICAL across all frames\n"
        f"- Lighting and color palette must be consistent within each scene\n"
        f"- Each prompt must be self-contained (100-250 words)\n"
        f"- Include the frame_id from above in your response\n"
        f"- Art style must be consistent: {project.style or 'cinematic'}\n"
    )

    provider = _get_provider()
    request = ProviderRequest(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=8192,
    )

    await _update_job_progress(job_id, 20)

    try:
        response = await provider.generate(request)
    except Exception as exc:
        await log_provider_run(
            project_id=project_id,
            operation="story_prompts",
            request=request,
            error=str(exc),
        )
        raise

    await log_provider_run(
        project_id=project_id,
        operation="story_prompts",
        request=request,
        response=response,
    )

    await _update_job_progress(job_id, 60)

    # Parse response
    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"Failed to parse story prompts response as JSON")

    frame_prompts = data.get("frame_prompts", [])
    shared_negative = data.get("shared_negative_prompt", "")
    style_summary = data.get("style_summary", "")

    await _update_job_progress(job_id, 80)

    # Update frame specs with generated prompts
    updated_count = 0
    async with async_session_factory() as session:
        for fp in frame_prompts:
            fid = fp.get("frame_id")
            prompt_text = fp.get("visual_prompt", "")
            style_anchor = fp.get("style_anchor", "")

            if not fid or not prompt_text:
                continue

            try:
                frame = (
                    await session.execute(
                        select(FrameSpec).where(FrameSpec.id == uuid.UUID(fid))
                    )
                ).scalar_one_or_none()

                if frame:
                    if style_anchor:
                        prompt_text = f"{prompt_text} Style: {style_anchor}."
                    frame.visual_prompt = prompt_text
                    frame.negative_prompt = shared_negative
                    updated_count += 1
            except Exception as e:
                logger.warning("Failed to update frame %s: %s", fid, e)

        await session.commit()

    await _update_job_progress(job_id, 100)

    logger.info(
        "story_prompts completed: project=%s frames_updated=%d/%d",
        project_id, updated_count, len(all_frames),
    )

    return {
        "project_id": project_id,
        "frames_total": len(all_frames),
        "frames_updated": updated_count,
        "style_summary": style_summary,
        "model": response.model,
        "tokens": response.input_tokens + response.output_tokens,
    }
