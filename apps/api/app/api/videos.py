"""Video generation API — shot-level clip generation + asset retrieval."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.shot import Shot
from shared.models.job import Job
from shared.schemas.job import JobResponse
from shared.storage import get_presigned_url
from app.services.queue import get_queue

router = APIRouter()


# ── Schemas ───────────────────────────────────────────


class VideoGenerateRequest(BaseModel):
    mode: str = Field(
        default="auto",
        pattern=r"^(auto|image_to_video|text_to_video)$",
        description="auto: uses frames if available, else text-only",
    )
    duration_override: float | None = Field(
        default=None, ge=1.0, le=30.0,
        description="Override shot duration (seconds)",
    )
    num_variants: int = Field(
        default=1, ge=1, le=3,
        description="Number of video variants to generate (1-3)",
    )


class VideoAssetResponse(BaseModel):
    id: UUID
    project_id: UUID
    parent_type: str
    parent_id: UUID
    asset_type: str
    storage_key: str | None
    filename: str | None
    mime_type: str | None
    file_size_bytes: int | None
    metadata_: dict | None = Field(None, alias="metadata_")
    version: int
    status: str
    is_selected: bool = False
    generation_batch: str | None = None
    quality_note: str | None = None
    created_at: datetime
    url: str | None = None


class VideoAssetListResponse(BaseModel):
    assets: list[VideoAssetResponse]
    total: int


# ── Endpoints ─────────────────────────────────────────


@router.post(
    "/{project_id}/shots/{shot_id}/video/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_shot_video(
    project_id: UUID,
    shot_id: UUID,
    body: VideoGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue a video generation job for a shot."""
    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise HTTPException(404, "Shot not found")

    req = body or VideoGenerateRequest()

    job = Job(
        job_type="video_generate",
        project_id=project_id,
        target_type="shot",
        target_id=shot_id,
        params={
            "project_id": str(project_id),
            "shot_id": str(shot_id),
            "mode": req.mode,
            "duration_override": req.duration_override,
            "num_variants": req.num_variants,
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

    shot.status = "generating_video"
    await db.flush()

    return job


@router.get(
    "/{project_id}/shots/{shot_id}/video/assets",
    response_model=VideoAssetListResponse,
)
async def list_shot_video_assets(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all video assets for a shot, with presigned URLs."""
    result = await db.execute(
        select(Asset)
        .where(
            Asset.parent_type == "shot",
            Asset.parent_id == shot_id,
            Asset.asset_type == "video",
        )
        .order_by(Asset.created_at.desc())
    )
    assets = list(result.scalars().all())

    responses = []
    for a in assets:
        url = None
        if a.storage_key and a.status == "ready":
            try:
                url = get_presigned_url(a.storage_key, expires_in=3600)
            except Exception:
                url = None

        responses.append(VideoAssetResponse(
            id=a.id,
            project_id=a.project_id,
            parent_type=a.parent_type,
            parent_id=a.parent_id,
            asset_type=a.asset_type,
            storage_key=a.storage_key,
            filename=a.filename,
            mime_type=a.mime_type,
            file_size_bytes=a.file_size_bytes,
            metadata_=a.metadata_,
            version=a.version,
            status=a.status,
            is_selected=a.is_selected,
            generation_batch=a.generation_batch,
            quality_note=a.quality_note,
            created_at=a.created_at,
            url=url,
        ))

    return VideoAssetListResponse(assets=responses, total=len(responses))
