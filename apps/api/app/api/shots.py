from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.schemas.job import JobResponse
from shared.schemas.shot import ShotListResponse, ShotResponse
from app.services.queue import get_queue

router = APIRouter()


@router.post(
    "/{project_id}/scenes/{scene_id}/shots/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_shots(
    project_id: UUID,
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    scene = (
        await db.execute(select(Scene).where(Scene.id == scene_id))
    ).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    job = Job(
        job_type="shot_plan",
        project_id=project_id,
        target_type="scene",
        target_id=scene_id,
        params={
            "project_id": str(project_id),
            "scene_id": str(scene_id),
            "script_version_id": str(scene.script_version_id),
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
    "/{project_id}/scenes/{scene_id}/shots",
    response_model=ShotListResponse,
)
async def list_shots(
    project_id: UUID,
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Shot).where(Shot.scene_id == scene_id).order_by(Shot.order_index)
    )
    shots = list(result.scalars().all())
    total_dur = sum(s.duration_sec or 0 for s in shots)
    return ShotListResponse(shots=shots, total=len(shots), total_duration_sec=total_dur)


@router.get(
    "/{project_id}/shots/{shot_id}",
    response_model=ShotResponse,
)
async def get_shot(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    return shot


@router.post(
    "/{project_id}/shots/{shot_id}/regenerate",
    response_model=JobResponse,
    status_code=201,
)
async def regenerate_shot(
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
        job_type="shot_regenerate",
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
