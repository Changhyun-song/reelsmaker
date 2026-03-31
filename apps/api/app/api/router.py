import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import get_db
from app.auth import get_current_user
from app.api.projects import router as projects_router
from app.api.jobs import router as jobs_router
from app.api.scripts import router as scripts_router
from app.api.scenes import router as scenes_router
from app.api.shots import router as shots_router
from app.api.frames import router as frames_router
from app.api.style_presets import router as style_presets_router
from app.api.characters import router as characters_router
from app.api.prompts import router as prompts_router
from app.api.images import router as images_router
from app.api.videos import router as videos_router
from app.api.tts import router as tts_router
from app.api.subtitles import router as subtitles_router
from app.api.timelines import router as timelines_router
from app.api.renders import router as renders_router
from app.api.selection import router as selection_router
from app.api.qa import router as qa_router
from app.api.exports import router as exports_router
from app.api.evaluations import router as evaluations_router
from app.api.continuity import router as continuity_router
from app.api.ops import router as ops_router
from app.api.billing import router as billing_router

settings = get_settings()
api_router = APIRouter()
api_router.include_router(ops_router, prefix="/ops", tags=["ops"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scripts_router, prefix="/projects", tags=["scripts"])
api_router.include_router(scenes_router, prefix="/projects", tags=["scenes"])
api_router.include_router(shots_router, prefix="/projects", tags=["shots"])
api_router.include_router(frames_router, prefix="/projects", tags=["frames"])
api_router.include_router(style_presets_router, prefix="/projects", tags=["styles"])
api_router.include_router(characters_router, prefix="/projects", tags=["characters"])
api_router.include_router(prompts_router, prefix="/projects", tags=["prompts"])
api_router.include_router(images_router, prefix="/projects", tags=["images"])
api_router.include_router(videos_router, prefix="/projects", tags=["videos"])
api_router.include_router(tts_router, prefix="/projects", tags=["tts"])
api_router.include_router(subtitles_router, prefix="/projects", tags=["subtitles"])
api_router.include_router(timelines_router, prefix="/projects", tags=["timelines"])
api_router.include_router(renders_router, prefix="/projects", tags=["render"])
api_router.include_router(selection_router, prefix="/projects", tags=["selection"])
api_router.include_router(qa_router, prefix="/projects", tags=["qa"])
api_router.include_router(exports_router, prefix="/projects", tags=["export"])
api_router.include_router(evaluations_router, prefix="/projects", tags=["evaluations"])
api_router.include_router(continuity_router, prefix="/projects", tags=["continuity"])


@api_router.get("/projects/{project_id}/progress", tags=["projects"])
async def project_progress(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return pipeline completion status for each stage."""
    from shared.models import (
        ScriptVersion, Scene, Shot, FrameSpec, Asset,
        VoiceTrack, SubtitleTrack, Timeline, RenderJob, Job,
    )
    from sqlalchemy import func, select

    sv = await db.execute(
        select(ScriptVersion.id, ScriptVersion.status)
        .where(ScriptVersion.project_id == project_id)
        .order_by(ScriptVersion.version.desc())
        .limit(1)
    )
    script_row = sv.first()
    script_id = script_row[0] if script_row else None
    has_script = script_row is not None and script_row[1] in ("planned", "structured")

    scene_count = 0
    shot_count = 0
    frame_count = 0
    if script_id:
        scene_count = (await db.execute(
            select(func.count()).where(Scene.script_version_id == script_id)
        )).scalar() or 0
        if scene_count > 0:
            scene_ids = [r[0] for r in (await db.execute(
                select(Scene.id).where(Scene.script_version_id == script_id)
            )).all()]
            shot_count = (await db.execute(
                select(func.count()).where(Shot.scene_id.in_(scene_ids))
            )).scalar() or 0
            if shot_count > 0:
                shot_ids = [r[0] for r in (await db.execute(
                    select(Shot.id).where(Shot.scene_id.in_(scene_ids))
                )).all()]
                frame_count = (await db.execute(
                    select(func.count()).where(FrameSpec.shot_id.in_(shot_ids))
                )).scalar() or 0

    image_count = (await db.execute(
        select(func.count()).where(Asset.project_id == project_id, Asset.asset_type == "image")
    )).scalar() or 0

    video_count = (await db.execute(
        select(func.count()).where(Asset.project_id == project_id, Asset.asset_type == "video")
    )).scalar() or 0

    voice_count = (await db.execute(
        select(func.count()).where(VoiceTrack.project_id == project_id)
    )).scalar() or 0

    subtitle_count = (await db.execute(
        select(func.count()).where(SubtitleTrack.project_id == project_id)
    )).scalar() or 0

    timeline_count = (await db.execute(
        select(func.count()).where(Timeline.project_id == project_id)
    )).scalar() or 0

    render_completed = (await db.execute(
        select(func.count()).where(
            RenderJob.project_id == project_id, RenderJob.status == "completed"
        )
    )).scalar() or 0

    running_jobs = (await db.execute(
        select(Job.id, Job.job_type, Job.status, Job.progress)
        .where(Job.project_id == project_id, Job.status.in_(["queued", "running"]))
        .order_by(Job.created_at.desc())
        .limit(5)
    )).all()

    active_jobs = [
        {"id": str(j[0]), "job_type": j[1], "status": j[2], "progress": j[3]}
        for j in running_jobs
    ]

    return {
        "script": has_script,
        "scenes": scene_count,
        "shots": shot_count,
        "frames": frame_count,
        "images": image_count,
        "videos": video_count,
        "voices": voice_count,
        "subtitles": subtitle_count,
        "timelines": timeline_count,
        "renders": render_completed,
        "active_jobs": active_jobs,
    }


@api_router.get("/projects/{project_id}/pipeline-inspect", tags=["projects"])
async def pipeline_inspect(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Full pipeline diagnostic snapshot for a project."""
    from shared.models import (
        ScriptVersion, Scene, Shot, FrameSpec, Asset,
        VoiceTrack, SubtitleTrack, Timeline, RenderJob, Job,
    )
    from shared.models.provider_run import ProviderRun
    from sqlalchemy import func, select, desc

    pid = project_id
    stages: dict = {}

    # ── Script ──
    sv_row = (await db.execute(
        select(
            ScriptVersion.id, ScriptVersion.status, ScriptVersion.version,
            ScriptVersion.created_at, ScriptVersion.updated_at,
        )
        .where(ScriptVersion.project_id == pid)
        .order_by(ScriptVersion.version.desc())
        .limit(1)
    )).first()
    script_id = sv_row[0] if sv_row else None
    stages["script"] = {
        "exists": sv_row is not None,
        "status": sv_row[1] if sv_row else None,
        "version": sv_row[2] if sv_row else None,
        "updated_at": str(sv_row[4] or sv_row[3]) if sv_row else None,
    }

    # ── Scene / Shot / Frame counts + structural warnings ──
    scene_count = shot_count = frame_count = 0
    scene_ids: list = []
    shot_ids: list = []
    frames_with_prompt = 0
    frames_with_story_prompt = 0

    if script_id:
        scene_count = (await db.execute(
            select(func.count()).where(Scene.script_version_id == script_id)
        )).scalar() or 0
        if scene_count > 0:
            scene_ids = [r[0] for r in (await db.execute(
                select(Scene.id).where(Scene.script_version_id == script_id)
            )).all()]
            shot_count = (await db.execute(
                select(func.count()).where(Shot.scene_id.in_(scene_ids))
            )).scalar() or 0
            if shot_count > 0:
                shot_ids = [r[0] for r in (await db.execute(
                    select(Shot.id).where(Shot.scene_id.in_(scene_ids))
                )).all()]
                frame_count = (await db.execute(
                    select(func.count()).where(FrameSpec.shot_id.in_(shot_ids))
                )).scalar() or 0
                frames_with_prompt = (await db.execute(
                    select(func.count()).where(
                        FrameSpec.shot_id.in_(shot_ids),
                        FrameSpec.visual_prompt.isnot(None),
                        FrameSpec.visual_prompt != "",
                    )
                )).scalar() or 0

    warnings: list[str] = []
    if scene_count > 0 and shot_count == 0:
        warnings.append("씬은 있지만 샷이 0개 — 샷 구성이 실행되지 않았습니다")
    if shot_count > 0 and frame_count == 0:
        warnings.append("샷은 있지만 프레임이 0개 — 프레임 구성이 실행되지 않았습니다")
    if frame_count > 0 and frames_with_prompt == 0:
        warnings.append("프레임은 있지만 프롬프트가 0개 — 스토리 프롬프트 또는 이미지 생성을 실행하세요")

    stages["scene"] = {"count": scene_count, "updated_at": None}
    stages["shot"] = {"count": shot_count, "updated_at": None}
    stages["frame"] = {
        "count": frame_count,
        "with_prompt": frames_with_prompt,
        "story_prompt_ratio": f"{frames_with_prompt}/{frame_count}" if frame_count else "0/0",
        "updated_at": None,
    }

    # ── Image / Video / TTS / Subtitle / Timeline / Render ──
    image_count = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "image")
    )).scalar() or 0
    image_ready = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "image", Asset.status == "ready")
    )).scalar() or 0

    video_count = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "video")
    )).scalar() or 0
    video_ready = (await db.execute(
        select(func.count()).where(Asset.project_id == pid, Asset.asset_type == "video", Asset.status == "ready")
    )).scalar() or 0

    voice_count = (await db.execute(
        select(func.count()).where(VoiceTrack.project_id == pid)
    )).scalar() or 0
    subtitle_count = (await db.execute(
        select(func.count()).where(SubtitleTrack.project_id == pid)
    )).scalar() or 0
    timeline_count = (await db.execute(
        select(func.count()).where(Timeline.project_id == pid)
    )).scalar() or 0
    render_count = (await db.execute(
        select(func.count()).where(RenderJob.project_id == pid)
    )).scalar() or 0
    render_completed = (await db.execute(
        select(func.count()).where(RenderJob.project_id == pid, RenderJob.status == "completed")
    )).scalar() or 0

    stages["image"] = {"total": image_count, "ready": image_ready}
    stages["video"] = {"total": video_count, "ready": video_ready}
    stages["tts"] = {"count": voice_count}
    stages["subtitle"] = {"count": subtitle_count}
    stages["timeline"] = {"count": timeline_count}
    stages["render"] = {"total": render_count, "completed": render_completed}

    # ── Recent jobs (last 20, all statuses) ──
    recent_jobs_rows = (await db.execute(
        select(
            Job.id, Job.job_type, Job.status, Job.progress,
            Job.error_message, Job.created_at, Job.completed_at,
            Job.result, Job.retry_count, Job.max_retries,
        )
        .where(Job.project_id == pid)
        .order_by(desc(Job.created_at))
        .limit(20)
    )).all()

    recent_jobs = []
    latest_by_type: dict[str, dict] = {}
    for j in recent_jobs_rows:
        jd = {
            "id": str(j[0]), "job_type": j[1], "status": j[2],
            "progress": j[3], "error_message": j[4],
            "created_at": str(j[5]) if j[5] else None,
            "completed_at": str(j[6]) if j[6] else None,
            "result_preview": _truncate_dict(j[7], 300) if j[7] else None,
            "retry_count": j[8], "max_retries": j[9],
        }
        recent_jobs.append(jd)
        if j[1] not in latest_by_type:
            latest_by_type[j[1]] = jd

    # ── Provider runs (recent 10) ──
    provider_rows = (await db.execute(
        select(
            ProviderRun.provider, ProviderRun.operation, ProviderRun.model,
            ProviderRun.status, ProviderRun.latency_ms, ProviderRun.error_message,
            ProviderRun.created_at, ProviderRun.cost_estimate,
        )
        .where(ProviderRun.project_id == pid)
        .order_by(desc(ProviderRun.created_at))
        .limit(10)
    )).all()

    provider_runs = [
        {
            "provider": r[0], "operation": r[1], "model": r[2],
            "status": r[3], "latency_ms": r[4], "error_message": r[5],
            "created_at": str(r[6]) if r[6] else None,
            "cost_estimate": r[7],
        }
        for r in provider_rows
    ]

    # ── Prompt samples (first 3 frames that have visual_prompt) ──
    prompt_samples = []
    if frame_count > 0 and shot_ids:
        sample_frames = (await db.execute(
            select(FrameSpec.id, FrameSpec.frame_role, FrameSpec.visual_prompt, FrameSpec.negative_prompt)
            .where(FrameSpec.shot_id.in_(shot_ids), FrameSpec.visual_prompt.isnot(None))
            .order_by(FrameSpec.order_index)
            .limit(3)
        )).all()
        for sf in sample_frames:
            prompt_samples.append({
                "frame_id": str(sf[0]),
                "frame_role": sf[1],
                "visual_prompt_preview": (sf[2] or "")[:300],
                "has_negative": bool(sf[3]),
            })

    # ── Health / providers info ──
    providers = {
        "image": settings.image_provider,
        "video": settings.video_provider,
        "tts": settings.tts_provider,
        "text": "claude" if settings.anthropic_api_key else "none",
    }

    return {
        "project_id": pid,
        "stages": stages,
        "warnings": warnings,
        "recent_jobs": recent_jobs,
        "latest_by_type": latest_by_type,
        "provider_runs": provider_runs,
        "prompt_samples": prompt_samples,
        "providers": providers,
    }


def _truncate_dict(d: dict | None, max_chars: int = 300) -> dict | str:
    if not d:
        return {}
    import json
    s = json.dumps(d, ensure_ascii=False, default=str)
    if len(s) > max_chars:
        return s[:max_chars] + "..."
    return d


@api_router.get("/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db)):
    checks: dict[str, str] = {"api": "ok"}

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    try:
        from app.services.storage import s3_client
        s3_client.head_bucket(Bucket=settings.s3_bucket)
        checks["storage"] = "ok"
    except Exception as e:
        checks["storage"] = f"error: {e}"

    checks["providers"] = {
        "image": settings.image_provider,
        "video": settings.video_provider,
        "tts": settings.tts_provider,
        "text": "claude" if settings.anthropic_api_key else "none",
    }

    all_ok = all(v == "ok" for k, v in checks.items() if k != "providers")
    return {"status": "ok" if all_ok else "degraded", "services": checks}
