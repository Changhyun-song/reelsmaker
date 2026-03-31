from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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


class FrameUpdateRequest(BaseModel):
    visual_prompt: str | None = None
    negative_prompt: str | None = None
    dialogue: str | None = None
    duration_ms: int | None = Field(None, ge=500, le=30000)
    composition: str | None = None
    mood: str | None = None
    action_pose: str | None = None
    background_description: str | None = None
    continuity_notes: str | None = None
    forbidden_elements: str | None = None


class ShotUpdateRequest(BaseModel):
    narration_segment: str | None = None
    description: str | None = None
    duration_sec: float | None = Field(None, ge=0.5, le=60)
    camera_movement: str | None = None
    emotion: str | None = None


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


# ── Storyboard editing endpoints ──────────────────────


@router.patch(
    "/{project_id}/frames/{frame_id}",
    response_model=FrameSpecResponse,
)
async def update_frame(
    project_id: UUID,
    frame_id: UUID,
    body: FrameUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update editable fields of a frame spec (storyboard editing)."""
    frame = (
        await db.execute(select(FrameSpec).where(FrameSpec.id == frame_id))
    ).scalar_one_or_none()
    if not frame:
        raise HTTPException(status_code=404, detail="FrameSpec not found")

    for field_name in body.model_fields_set:
        val = getattr(body, field_name)
        if val is not None:
            setattr(frame, field_name, val)

    await db.flush()
    await db.refresh(frame)
    return frame


@router.patch(
    "/{project_id}/shots/{shot_id}/edit",
    response_model=dict,
)
async def update_shot_storyboard(
    project_id: UUID,
    shot_id: UUID,
    body: ShotUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update editable fields of a shot (storyboard editing)."""
    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    changed_fields: list[str] = []
    for field_name in body.model_fields_set:
        val = getattr(body, field_name)
        if val is not None:
            old = getattr(shot, field_name)
            if old != val:
                setattr(shot, field_name, val)
                changed_fields.append(field_name)

    await db.flush()
    await db.refresh(shot)
    return {
        "id": str(shot.id),
        "changed_fields": changed_fields,
        "narration_segment": shot.narration_segment,
        "description": shot.description,
        "duration_sec": shot.duration_sec,
        "camera_movement": shot.camera_movement,
        "emotion": shot.emotion,
    }
