"""Render API — enqueue render job, CRUD, output asset URL."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.job import Job
from shared.models.render_job import RenderJob
from shared.models.timeline import Timeline
from shared.schemas.job import JobResponse
from shared.storage import get_presigned_url
from app.services.queue import get_queue

router = APIRouter()


class RenderRequest(BaseModel):
    timeline_id: UUID
    burn_subtitles: bool = False


class RenderJobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    timeline_id: str
    status: str
    progress: int
    ffmpeg_command: str | None = None
    error_message: str | None = None
    output_asset_id: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class RenderOutputResponse(BaseModel):
    render_job_id: str
    status: str
    output_url: str | None = None
    duration_sec: float | None = None
    file_size_bytes: int | None = None
    width: int | None = None
    height: int | None = None


@router.post(
    "/{project_id}/render",
    response_model=JobResponse,
    status_code=201,
)
async def start_render(
    project_id: UUID,
    body: RenderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a final render job for a timeline."""
    tl = (
        await db.execute(
            select(Timeline).where(
                Timeline.id == body.timeline_id,
                Timeline.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not tl:
        raise HTTPException(404, "Timeline not found")
    if tl.status != "composed":
        raise HTTPException(400, f"Timeline status is '{tl.status}', must be 'composed'")

    # Create RenderJob row
    rj = RenderJob(
        project_id=project_id,
        timeline_id=body.timeline_id,
        output_settings=tl.segments.get("output_settings", {}) if tl.segments else {},
        status="queued",
        progress=0,
    )
    db.add(rj)
    await db.flush()
    await db.refresh(rj)

    # Create Job row
    job = Job(
        job_type="render_final",
        project_id=project_id,
        target_type="timeline",
        target_id=body.timeline_id,
        params={
            "project_id": str(project_id),
            "timeline_id": str(body.timeline_id),
            "render_job_id": str(rj.id),
            "burn_subtitles": body.burn_subtitles,
        },
        max_retries=1,
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
    "/{project_id}/render-jobs",
)
async def list_render_jobs(
    project_id: UUID,
    timeline_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(RenderJob).where(RenderJob.project_id == project_id)
    if timeline_id:
        q = q.where(RenderJob.timeline_id == timeline_id)
    q = q.order_by(RenderJob.created_at.desc())

    result = await db.execute(q)
    jobs = list(result.scalars().all())

    return {
        "render_jobs": [
            {
                "id": str(rj.id),
                "timeline_id": str(rj.timeline_id),
                "status": rj.status,
                "progress": rj.progress,
                "error_message": rj.error_message,
                "output_asset_id": str(rj.output_asset_id) if rj.output_asset_id else None,
                "created_at": str(rj.created_at),
                "started_at": str(rj.started_at) if rj.started_at else None,
                "completed_at": str(rj.completed_at) if rj.completed_at else None,
            }
            for rj in jobs
        ],
        "total": len(jobs),
    }


@router.get(
    "/{project_id}/render-jobs/{render_job_id}/output",
    response_model=RenderOutputResponse,
)
async def get_render_output(
    project_id: UUID,
    render_job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the output video URL and metadata for a completed render."""
    rj = (
        await db.execute(
            select(RenderJob).where(
                RenderJob.id == render_job_id,
                RenderJob.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not rj:
        raise HTTPException(404, "RenderJob not found")

    output_url = None
    duration_sec = None
    file_size = None
    width = None
    height = None

    if rj.output_asset_id:
        asset = (
            await db.execute(select(Asset).where(Asset.id == rj.output_asset_id))
        ).scalar_one_or_none()
        if asset and asset.storage_key:
            output_url = get_presigned_url(asset.storage_key, expires_in=7200)
            file_size = asset.file_size_bytes
            if asset.metadata_:
                duration_sec = asset.metadata_.get("duration_sec")
                width = asset.metadata_.get("width")
                height = asset.metadata_.get("height")

    return RenderOutputResponse(
        render_job_id=str(rj.id),
        status=rj.status,
        output_url=output_url,
        duration_sec=duration_sec,
        file_size_bytes=file_size,
        width=width,
        height=height,
    )
