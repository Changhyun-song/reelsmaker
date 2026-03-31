"""Image generation API — job enqueue + asset retrieval + presigned URLs."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.frame_spec import FrameSpec
from shared.models.job import Job
from shared.schemas.job import JobResponse
from shared.storage import get_presigned_url
from app.services.queue import get_queue

router = APIRouter()


# ── Schemas ───────────────────────────────────────────


class ImageGenerateRequest(BaseModel):
    num_variants: int = Field(default=2, ge=1, le=4)


class AssetResponse(BaseModel):
    model_config = {"from_attributes": True}

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


class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    total: int


class StoryPromptsRequest(BaseModel):
    script_version_id: str


# ── Endpoints ─────────────────────────────────────────


@router.post(
    "/{project_id}/story-prompts/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_story_prompts(
    project_id: UUID,
    body: StoryPromptsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate rich visual prompts for ALL frames based on full story context.

    This step should run BEFORE image generation to ensure high-quality,
    story-coherent prompts with visual continuity across all cuts.
    """
    job = Job(
        job_type="story_prompts",
        project_id=project_id,
        params={
            "project_id": str(project_id),
            "script_version_id": body.script_version_id,
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


@router.post(
    "/{project_id}/frames/{frame_id}/images/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_frame_images(
    project_id: UUID,
    frame_id: UUID,
    body: ImageGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue image generation job for a frame spec."""
    frame = (
        await db.execute(select(FrameSpec).where(FrameSpec.id == frame_id))
    ).scalar_one_or_none()
    if not frame:
        raise HTTPException(404, "FrameSpec not found")

    num_variants = body.num_variants if body else 2

    job = Job(
        job_type="image_generate",
        project_id=project_id,
        target_type="frame_spec",
        target_id=frame_id,
        params={
            "project_id": str(project_id),
            "frame_id": str(frame_id),
            "num_variants": num_variants,
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

    frame.status = "generating"
    await db.flush()

    return job


@router.get(
    "/{project_id}/frames/{frame_id}/assets",
    response_model=AssetListResponse,
)
async def list_frame_assets(
    project_id: UUID,
    frame_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all image assets for a frame spec, with presigned URLs."""
    result = await db.execute(
        select(Asset)
        .where(Asset.parent_type == "frame_spec", Asset.parent_id == frame_id)
        .order_by(Asset.created_at.desc())
    )
    assets = list(result.scalars().all())

    responses = []
    for a in assets:
        url = None
        if a.storage_key and a.status in ("ready", "approved"):
            try:
                url = get_presigned_url(a.storage_key, expires_in=3600)
            except Exception:
                url = None

        resp = AssetResponse(
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
        )
        responses.append(resp)

    return AssetListResponse(assets=responses, total=len(responses))


@router.get(
    "/{project_id}/assets/{asset_id}/url",
)
async def get_asset_url(
    project_id: UUID,
    asset_id: UUID,
    expires_in: int = Query(default=3600, ge=60, le=86400),
    db: AsyncSession = Depends(get_db),
):
    """Get a presigned URL for an asset."""
    asset = (
        await db.execute(select(Asset).where(Asset.id == asset_id))
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if not asset.storage_key:
        raise HTTPException(400, "Asset has no storage key")

    url = get_presigned_url(asset.storage_key, expires_in=expires_in)
    return {"url": url, "expires_in": expires_in}
