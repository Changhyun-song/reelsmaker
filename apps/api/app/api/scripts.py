from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.models.project import Project
from shared.models.script_version import ScriptVersion
from shared.schemas.job import JobResponse
from shared.schemas.script import (
    ScriptPlanRequest,
    ScriptVersionListResponse,
    ScriptVersionResponse,
)
from app.services.queue import get_queue

router = APIRouter()


@router.post(
    "/{project_id}/scripts/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_script_plan(
    project_id: UUID,
    data: ScriptPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = Job(
        job_type="script_generate",
        project_id=project_id,
        target_type="project",
        target_id=project_id,
        params={
            "project_id": str(project_id),
            "topic": data.topic,
            "target_audience": data.target_audience,
            "tone": data.tone,
            "duration_sec": data.duration_sec,
            "format": data.format,
            "language": data.language,
            "constraints": data.constraints,
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
    "/{project_id}/scripts",
    response_model=ScriptVersionListResponse,
)
async def list_script_versions(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    total = (
        await db.execute(
            select(func.count(ScriptVersion.id)).where(
                ScriptVersion.project_id == project_id
            )
        )
    ).scalar() or 0

    result = await db.execute(
        select(ScriptVersion)
        .where(ScriptVersion.project_id == project_id)
        .order_by(ScriptVersion.version.desc())
    )
    versions = result.scalars().all()
    return ScriptVersionListResponse(versions=versions, total=total)


@router.get(
    "/{project_id}/scripts/{version_id}",
    response_model=ScriptVersionResponse,
)
async def get_script_version(
    project_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScriptVersion).where(
            ScriptVersion.id == version_id,
            ScriptVersion.project_id == project_id,
        )
    )
    sv = result.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Script version not found")
    return sv
