from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.frame_spec import FrameSpec
from shared.models.job import Job
from shared.models.shot import Shot
from shared.schemas.frame_spec import FrameSpecListResponse, FrameSpecResponse
from shared.schemas.job import JobResponse
from app.services.queue import get_queue

router = APIRouter()


@router.post(
    "/{project_id}/shots/{shot_id}/frames/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_frames(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    job = Job(
        job_type="frame_plan",
        project_id=project_id,
        target_type="shot",
        target_id=shot_id,
        params={
            "project_id": str(project_id),
            "shot_id": str(shot_id),
            "scene_id": str(shot.scene_id),
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
    "/{project_id}/shots/{shot_id}/frames",
    response_model=FrameSpecListResponse,
)
async def list_frames(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FrameSpec)
        .where(FrameSpec.shot_id == shot_id)
        .order_by(FrameSpec.order_index)
    )
    frames = list(result.scalars().all())
    return FrameSpecListResponse(frames=frames, total=len(frames))


@router.get(
    "/{project_id}/frames/{frame_id}",
    response_model=FrameSpecResponse,
)
async def get_frame(
    project_id: UUID,
    frame_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    frame = (
        await db.execute(select(FrameSpec).where(FrameSpec.id == frame_id))
    ).scalar_one_or_none()
    if not frame:
        raise HTTPException(status_code=404, detail="FrameSpec not found")
    return frame


@router.post(
    "/{project_id}/frames/{frame_id}/regenerate",
    response_model=JobResponse,
    status_code=201,
)
async def regenerate_frame(
    project_id: UUID,
    frame_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    frame = (
        await db.execute(select(FrameSpec).where(FrameSpec.id == frame_id))
    ).scalar_one_or_none()
    if not frame:
        raise HTTPException(status_code=404, detail="FrameSpec not found")

    job = Job(
        job_type="frame_regenerate",
        project_id=project_id,
        target_type="frame_spec",
        target_id=frame_id,
        params={
            "project_id": str(project_id),
            "frame_id": str(frame_id),
            "shot_id": str(frame.shot_id),
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
