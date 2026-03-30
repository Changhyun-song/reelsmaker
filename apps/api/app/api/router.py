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
        s3_client.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"

    checks["providers"] = {
        "image": settings.image_provider,
        "video": settings.video_provider,
        "tts": settings.tts_provider,
        "text": "claude" if settings.anthropic_api_key else "none",
    }

    all_ok = all(v == "ok" for k, v in checks.items() if k != "providers")
    return {"status": "ok" if all_ok else "degraded", "services": checks}
