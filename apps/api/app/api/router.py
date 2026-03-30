import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import get_db
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

settings = get_settings()
api_router = APIRouter()
api_router.include_router(ops_router, prefix="/ops", tags=["ops"])
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
