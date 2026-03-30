"""Subtitle API — generation job enqueue, track CRUD, SRT content."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.job import Job
from shared.models.subtitle_track import SubtitleTrack
from shared.schemas.job import JobResponse
from shared.schemas.subtitle_track import (
    SubtitleGenerateRequest,
    SubtitleTrackListResponse,
    SubtitleTrackResponse,
)
from shared.storage import get_presigned_url
from app.services.queue import get_queue

router = APIRouter()


@router.post(
    "/{project_id}/subtitles/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_subtitles(
    project_id: UUID,
    body: SubtitleGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue subtitle generation for a script version."""
    style = body.style or {}
    style_dict = style.model_dump() if hasattr(style, "model_dump") else {}

    job = Job(
        job_type="subtitle_generate",
        project_id=project_id,
        target_type="script_version",
        target_id=body.script_version_id,
        params={
            "project_id": str(project_id),
            "script_version_id": str(body.script_version_id),
            "format": body.format,
            "language": body.language,
            **style_dict,
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
    "/{project_id}/subtitles",
    response_model=SubtitleTrackListResponse,
)
async def list_subtitle_tracks(
    project_id: UUID,
    script_version_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List subtitle tracks, optionally filtered by script version."""
    q = select(SubtitleTrack).where(SubtitleTrack.project_id == project_id)
    if script_version_id:
        q = q.where(SubtitleTrack.script_version_id == script_version_id)
    q = q.order_by(SubtitleTrack.created_at.desc())

    result = await db.execute(q)
    tracks = list(result.scalars().all())
    return SubtitleTrackListResponse(tracks=tracks, total=len(tracks))


@router.get(
    "/{project_id}/subtitles/{track_id}",
    response_model=SubtitleTrackResponse,
)
async def get_subtitle_track(
    project_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    track = (
        await db.execute(
            select(SubtitleTrack).where(
                SubtitleTrack.id == track_id,
                SubtitleTrack.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not track:
        raise HTTPException(404, "SubtitleTrack not found")
    return track


@router.get(
    "/{project_id}/subtitles/{track_id}/content",
    response_class=PlainTextResponse,
)
async def get_subtitle_content(
    project_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return raw SRT/VTT content as plain text."""
    track = (
        await db.execute(
            select(SubtitleTrack).where(
                SubtitleTrack.id == track_id,
                SubtitleTrack.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not track:
        raise HTTPException(404, "SubtitleTrack not found")
    if not track.content:
        raise HTTPException(404, "No content available")
    return PlainTextResponse(
        content=track.content,
        media_type="text/plain; charset=utf-8",
    )


@router.get(
    "/{project_id}/subtitles/{track_id}/download-url",
)
async def get_subtitle_download_url(
    project_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get presigned URL for downloading the subtitle file."""
    track = (
        await db.execute(
            select(SubtitleTrack).where(
                SubtitleTrack.id == track_id,
                SubtitleTrack.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not track or not track.asset_id:
        raise HTTPException(404, "No downloadable subtitle asset")

    from shared.models.asset import Asset
    asset = (
        await db.execute(select(Asset).where(Asset.id == track.asset_id))
    ).scalar_one_or_none()
    if not asset or not asset.storage_key:
        raise HTTPException(404, "Asset not found")

    url = get_presigned_url(asset.storage_key, expires_in=3600)
    return {"url": url, "format": track.format, "filename": asset.filename}
