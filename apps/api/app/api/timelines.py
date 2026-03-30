"""Timeline API — compose job enqueue, CRUD, summary."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.models.timeline import Timeline
from shared.schemas.job import JobResponse
from shared.schemas.timeline import (
    TimelineData,
    TimelineListResponse,
    TimelineResponse,
    TimelineSummary,
)
from app.services.queue import get_queue

router = APIRouter()


class TimelineComposeRequest(BaseModel):
    script_version_id: UUID
    output_width: int = Field(default=1920)
    output_height: int = Field(default=1080)
    output_fps: int = Field(default=30)


@router.post(
    "/{project_id}/timelines/compose",
    response_model=JobResponse,
    status_code=201,
)
async def compose_timeline(
    project_id: UUID,
    body: TimelineComposeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue timeline composition for a script version."""
    job = Job(
        job_type="timeline_compose",
        project_id=project_id,
        target_type="script_version",
        target_id=body.script_version_id,
        params={
            "project_id": str(project_id),
            "script_version_id": str(body.script_version_id),
            "output_width": body.output_width,
            "output_height": body.output_height,
            "output_fps": body.output_fps,
        },
        max_retries=2,
        status="queued",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    pool = await get_queue()
    arq_job = await pool.enqueue_job("run_job", str(job.id))
    job.arq_job_id = arq_job.job_id
    await db.flush()
    await db.refresh(job)
    return job


@router.get(
    "/{project_id}/timelines",
    response_model=TimelineListResponse,
)
async def list_timelines(
    project_id: UUID,
    script_version_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Timeline).where(Timeline.project_id == project_id)
    if script_version_id:
        q = q.where(Timeline.script_version_id == script_version_id)
    q = q.order_by(Timeline.created_at.desc())

    result = await db.execute(q)
    timelines = list(result.scalars().all())
    return TimelineListResponse(timelines=timelines, total=len(timelines))


@router.get(
    "/{project_id}/timelines/{timeline_id}",
    response_model=TimelineResponse,
)
async def get_timeline(
    project_id: UUID,
    timeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    tl = (
        await db.execute(
            select(Timeline).where(
                Timeline.id == timeline_id,
                Timeline.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not tl:
        raise HTTPException(404, "Timeline not found")
    return tl


@router.get(
    "/{project_id}/timelines/{timeline_id}/summary",
    response_model=TimelineSummary,
)
async def get_timeline_summary(
    project_id: UUID,
    timeline_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return a lightweight summary of a timeline for UI display."""
    tl = (
        await db.execute(
            select(Timeline).where(
                Timeline.id == timeline_id,
                Timeline.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not tl:
        raise HTTPException(404, "Timeline not found")

    data = tl.segments or {}

    video_segs = data.get("video_segments", [])
    audio_segs = data.get("audio_segments", [])
    warnings = data.get("warnings", [])

    shots_with_video = sum(1 for s in video_segs if s.get("asset_type") == "video")
    shots_with_image = sum(1 for s in video_segs if s.get("asset_type") == "image")
    shots_missing = sum(1 for s in video_segs if s.get("asset_type") == "missing")
    shots_with_audio = sum(1 for s in audio_segs if s.get("status") == "ready")
    shots_missing_audio = sum(1 for s in audio_segs if s.get("status") == "missing")

    return TimelineSummary(
        id=str(tl.id),
        status=tl.status,
        total_duration_ms=tl.total_duration_ms or 0,
        total_shots=len(video_segs),
        shots_with_video=shots_with_video,
        shots_with_image_only=shots_with_image,
        shots_missing_visual=shots_missing,
        shots_with_audio=shots_with_audio,
        shots_missing_audio=shots_missing_audio,
        has_subtitle=bool(data.get("subtitle_track_id")),
        has_bgm=bool(data.get("bgm_asset_id")),
        warnings=warnings,
        created_at=str(tl.created_at) if tl.created_at else "",
    )
