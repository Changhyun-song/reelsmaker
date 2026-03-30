from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.schemas.job import JobEnqueue, JobListResponse, JobResponse
from app.services.queue import get_queue

router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=201)
async def enqueue_job(data: JobEnqueue, db: AsyncSession = Depends(get_db)):
    job = Job(
        job_type=data.job_type.value,
        project_id=data.project_id,
        target_type=data.target_type,
        target_id=data.target_id,
        params=data.params,
        max_retries=data.max_retries,
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


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status: str | None = Query(None),
    job_type: str | None = Query(None),
    project_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job)
    count_query = select(func.count(Job.id))

    if status:
        query = query.where(Job.status == status)
        count_query = count_query.where(Job.status == status)
    if job_type:
        query = query.where(Job.job_type == job_type)
        count_query = count_query.where(Job.job_type == job_type)
    if project_id:
        query = query.where(Job.project_id == project_id)
        count_query = count_query.where(Job.project_id == project_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Job.created_at.desc()).offset(offset).limit(limit)
    )
    return JobListResponse(jobs=result.scalars().all(), total=total)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Only failed/cancelled jobs can be retried")

    job.status = "queued"
    job.progress = 0
    job.error_message = None
    job.error_traceback = None
    job.started_at = None
    job.completed_at = None
    await db.flush()

    pool = await get_queue()
    arq_job = await pool.enqueue_job("run_job", str(job.id))
    job.arq_job_id = arq_job.job_id
    await db.flush()
    await db.refresh(job)
    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("queued",):
        raise HTTPException(status_code=400, detail="Only queued jobs can be cancelled")

    job.status = "cancelled"
    await db.flush()
    await db.refresh(job)
    return job
