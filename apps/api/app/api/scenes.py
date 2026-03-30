from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.models.scene import Scene
from shared.models.script_version import ScriptVersion
from shared.schemas.job import JobResponse
from shared.schemas.scene import SceneListResponse, SceneResponse
from app.services.queue import get_queue

router = APIRouter()


@router.post(
    "/{project_id}/scripts/{version_id}/scenes/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_scenes(
    project_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    sv = (
        await db.execute(
            select(ScriptVersion).where(
                ScriptVersion.id == version_id,
                ScriptVersion.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Script version not found")

    job = Job(
        job_type="scene_plan",
        project_id=project_id,
        target_type="script_version",
        target_id=version_id,
        params={
            "project_id": str(project_id),
            "script_version_id": str(version_id),
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
    "/{project_id}/scripts/{version_id}/scenes",
    response_model=SceneListResponse,
)
async def list_scenes(
    project_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    sv = (
        await db.execute(
            select(ScriptVersion).where(
                ScriptVersion.id == version_id,
                ScriptVersion.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Script version not found")

    result = await db.execute(
        select(Scene)
        .where(Scene.script_version_id == version_id)
        .order_by(Scene.order_index)
    )
    scenes = list(result.scalars().all())
    total_dur = sum(s.duration_estimate_sec or 0 for s in scenes)
    return SceneListResponse(scenes=scenes, total=len(scenes), total_duration_sec=total_dur)


@router.get(
    "/{project_id}/scenes/{scene_id}",
    response_model=SceneResponse,
)
async def get_scene(
    project_id: UUID,
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    scene = (await db.execute(select(Scene).where(Scene.id == scene_id))).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.post(
    "/{project_id}/scenes/{scene_id}/regenerate",
    response_model=JobResponse,
    status_code=201,
)
async def regenerate_scene(
    project_id: UUID,
    scene_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    scene = (await db.execute(select(Scene).where(Scene.id == scene_id))).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    job = Job(
        job_type="scene_regenerate",
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


@router.patch(
    "/{project_id}/scenes/{scene_id}/status",
    response_model=SceneResponse,
)
async def update_scene_status(
    project_id: UUID,
    scene_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    scene = (await db.execute(select(Scene).where(Scene.id == scene_id))).scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    new_status = body.get("status")
    allowed = {"drafted", "approved", "needs_revision"}
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {allowed}")

    scene.status = new_status
    await db.flush()
    await db.refresh(scene)
    return scene
