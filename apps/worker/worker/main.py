import asyncio
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from arq import func
from arq.connections import RedisSettings
from sqlalchemy import select

from shared.config import get_settings
from shared.database import async_session_factory
from shared.models.job import Job

from shared.config import setup_logging

settings = get_settings()
logger = setup_logging("reelsmaker.worker")


def _parse_redis_url(url: str) -> RedisSettings:
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int((parsed.path or "/0").lstrip("/") or "0"),
        password=parsed.password,
    )


# ── DB helpers ────────────────────────────────────────


async def _load_job(job_id: str) -> Job | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Job).where(Job.id == uuid.UUID(job_id))
        )
        return result.scalar_one_or_none()


async def _update_job(job_id: str, **kwargs) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Job).where(Job.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if not job:
            return
        for k, v in kwargs.items():
            setattr(job, k, v)
        await session.commit()


# ── Job handlers ──────────────────────────────────────


async def handle_demo(job_id: str, **params) -> dict:
    sleep_seconds = params.get("sleep_seconds", 5)
    should_fail = params.get("should_fail", False)

    for i in range(sleep_seconds):
        await asyncio.sleep(1)
        progress = int((i + 1) / sleep_seconds * 100)
        await _update_job(job_id, progress=progress)
        logger.info("demo job %s: progress %d%%", job_id, progress)

    if should_fail:
        raise RuntimeError("Demo job intentionally failed (should_fail=true)")

    return {"message": f"Demo completed after {sleep_seconds}s"}


async def handle_image_generate_stub(job_id: str, **params) -> dict:
    logger.info("image_generate_stub: job=%s params=%s", job_id, params)
    await asyncio.sleep(3)
    return {"status": "stub", "note": "Image provider integration pending"}


async def handle_video_generate_stub(job_id: str, **params) -> dict:
    logger.info("video_generate_stub: job=%s params=%s", job_id, params)
    await asyncio.sleep(3)
    return {"status": "stub", "note": "Video provider integration pending"}


async def handle_tts_generate_stub(job_id: str, **params) -> dict:
    logger.info("tts_generate_stub: job=%s params=%s", job_id, params)
    await asyncio.sleep(2)
    return {"status": "stub", "note": "TTS provider integration pending"}


async def handle_subtitle_generate_stub(job_id: str, **params) -> dict:
    logger.info("subtitle_generate_stub: job=%s params=%s", job_id, params)
    await asyncio.sleep(1)
    return {"status": "stub", "note": "Subtitle generation pending"}


async def handle_timeline_compose_stub(job_id: str, **params) -> dict:
    logger.info("timeline_compose_stub: job=%s params=%s", job_id, params)
    await asyncio.sleep(2)
    return {"status": "stub", "note": "FFmpeg integration pending"}


async def handle_render_final_stub(job_id: str, **params) -> dict:
    logger.info("render_final_stub: job=%s params=%s", job_id, params)
    await asyncio.sleep(3)
    return {"status": "stub", "note": "FFmpeg integration pending"}


def _build_handlers() -> dict[str, callable]:
    from worker.handlers.script import (
        handle_script_generate,
        handle_script_structure,
    )
    from worker.handlers.scene import (
        handle_scene_plan,
        handle_scene_regenerate,
    )
    from worker.handlers.shot import (
        handle_shot_plan,
        handle_shot_regenerate,
    )
    from worker.handlers.frame import (
        handle_frame_plan,
        handle_frame_regenerate,
    )
    from worker.handlers.image import (
        handle_image_generate,
    )
    from worker.handlers.video import (
        handle_video_generate,
    )
    from worker.handlers.tts import (
        handle_tts_generate,
    )
    from worker.handlers.subtitle import (
        handle_subtitle_generate,
    )
    from worker.handlers.timeline import (
        handle_timeline_compose,
    )
    from worker.handlers.render import (
        handle_render_final,
    )

    return {
        "demo": handle_demo,
        "script_generate": handle_script_generate,
        "script_structure": handle_script_structure,
        "scene_plan": handle_scene_plan,
        "scene_regenerate": handle_scene_regenerate,
        "shot_plan": handle_shot_plan,
        "shot_regenerate": handle_shot_regenerate,
        "frame_plan": handle_frame_plan,
        "frame_regenerate": handle_frame_regenerate,
        "image_generate": handle_image_generate,
        "video_generate": handle_video_generate,
        "tts_generate": handle_tts_generate,
        "subtitle_generate": handle_subtitle_generate,
        "timeline_compose": handle_timeline_compose,
        "render_final": handle_render_final,
    }


HANDLERS: dict[str, callable] = _build_handlers()


# ── Universal job dispatcher ─────────────────────────


async def run_job(ctx: dict, job_id: str) -> None:
    now = datetime.now(timezone.utc)
    logger.info("Picking up job %s", job_id)

    job = await _load_job(job_id)
    if not job:
        logger.error("Job %s not found in DB, skipping", job_id)
        return

    if job.status == "cancelled":
        logger.info("Job %s was cancelled, skipping", job_id)
        return

    await _update_job(job_id, status="running", started_at=now, progress=0)

    handler = HANDLERS.get(job.job_type)
    if not handler:
        await _update_job(
            job_id,
            status="failed",
            error_message=f"Unknown job type: {job.job_type}",
            completed_at=now,
        )
        logger.error("Unknown job type: %s", job.job_type)
        return

    try:
        result = await handler(job_id=job_id, **(job.params or {}))
        await _update_job(
            job_id,
            status="completed",
            progress=100,
            result=result,
            completed_at=datetime.now(timezone.utc),
        )
        logger.info("Job %s completed successfully", job_id)

    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Job %s failed: %s", job_id, e)

        job = await _load_job(job_id)
        if not job:
            return

        new_retry_count = job.retry_count + 1
        if new_retry_count < job.max_retries:
            defer_seconds = new_retry_count * 10
            await _update_job(
                job_id,
                status="queued",
                retry_count=new_retry_count,
                error_message=str(e),
                progress=0,
                started_at=None,
            )
            await ctx["redis"].enqueue_job(
                "run_job",
                job_id,
                _job_id=f"retry-{job_id}-{new_retry_count}",
                _defer_by=timedelta(seconds=defer_seconds),
            )
            logger.info(
                "Job %s scheduled for retry %d/%d in %ds",
                job_id,
                new_retry_count,
                job.max_retries,
                defer_seconds,
            )
        else:
            await _update_job(
                job_id,
                status="failed",
                retry_count=new_retry_count,
                error_message=str(e),
                error_traceback=tb[-2000:],
                completed_at=datetime.now(timezone.utc),
            )
            logger.error(
                "Job %s permanently failed after %d retries",
                job_id,
                new_retry_count,
            )


# ── arq lifecycle ─────────────────────────────────────


async def on_startup(ctx: dict) -> None:
    logger.info("ReelsMaker worker started — ready to process jobs")


async def on_shutdown(ctx: dict) -> None:
    logger.info("ReelsMaker worker shutting down")


class WorkerSettings:
    functions = [func(run_job, max_tries=1)]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = _parse_redis_url(settings.redis_url)
    max_jobs = 3
    job_timeout = 3600
