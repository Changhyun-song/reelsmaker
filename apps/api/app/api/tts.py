"""TTS API — job enqueue + voice track CRUD + voice list."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.job import Job
from shared.models.shot import Shot
from shared.models.voice_track import VoiceTrack
from shared.schemas.job import JobResponse
from shared.schemas.voice_track import (
    VoicePreset,
    VoiceTrackListResponse,
    VoiceTrackResponse,
)
from shared.storage import get_presigned_url
from app.services.queue import get_queue

router = APIRouter()


# ── Schemas ───────────────────────────────────────────


class TTSGenerateRequest(BaseModel):
    voice_id: str = Field(default="narrator-ko-male")
    language: str = Field(default="ko")
    speed: float = Field(default=1.0, ge=0.5, le=3.0)
    emotion: str = ""
    speaker_name: str = ""
    text_override: str | None = None


# ── Endpoints ─────────────────────────────────────────


@router.post(
    "/{project_id}/shots/{shot_id}/tts/generate",
    response_model=JobResponse,
    status_code=201,
)
async def generate_shot_tts(
    project_id: UUID,
    shot_id: UUID,
    body: TTSGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue TTS generation for a shot's narration."""
    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise HTTPException(404, "Shot not found")

    req = body or TTSGenerateRequest()

    if not req.text_override and not shot.narration_segment:
        raise HTTPException(400, "Shot has no narration text and no text_override provided")

    job = Job(
        job_type="tts_generate",
        project_id=project_id,
        target_type="shot",
        target_id=shot_id,
        params={
            "project_id": str(project_id),
            "shot_id": str(shot_id),
            "voice_id": req.voice_id,
            "language": req.language,
            "speed": req.speed,
            "emotion": req.emotion,
            "speaker_name": req.speaker_name,
            "text_override": req.text_override,
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
    "/{project_id}/shots/{shot_id}/tts",
    response_model=VoiceTrackListResponse,
)
async def list_shot_voice_tracks(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all voice tracks for a shot, with presigned audio URLs."""
    result = await db.execute(
        select(VoiceTrack)
        .where(VoiceTrack.shot_id == shot_id)
        .order_by(VoiceTrack.created_at.desc())
    )
    tracks = list(result.scalars().all())
    return VoiceTrackListResponse(voice_tracks=tracks, total=len(tracks))


@router.get(
    "/{project_id}/voice-tracks/{track_id}",
    response_model=VoiceTrackResponse,
)
async def get_voice_track(
    project_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    track = (
        await db.execute(select(VoiceTrack).where(VoiceTrack.id == track_id))
    ).scalar_one_or_none()
    if not track:
        raise HTTPException(404, "VoiceTrack not found")
    return track


@router.get(
    "/{project_id}/shots/{shot_id}/tts/audio-url",
)
async def get_shot_tts_audio_url(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get presigned URL for the latest ready TTS audio of a shot."""
    track = (
        await db.execute(
            select(VoiceTrack)
            .where(VoiceTrack.shot_id == shot_id, VoiceTrack.status == "ready")
            .order_by(VoiceTrack.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not track or not track.asset_id:
        raise HTTPException(404, "No ready TTS audio for this shot")

    asset = (
        await db.execute(select(Asset).where(Asset.id == track.asset_id))
    ).scalar_one_or_none()
    if not asset or not asset.storage_key:
        raise HTTPException(404, "Audio asset not found")

    url = get_presigned_url(asset.storage_key, expires_in=3600)
    return {
        "url": url,
        "voice_track_id": str(track.id),
        "duration_ms": track.duration_ms,
        "voice_id": track.voice_id,
    }


@router.get(
    "/{project_id}/voices",
    response_model=list[VoicePreset],
)
async def list_available_voices(project_id: UUID):
    """List available TTS voices from the configured provider."""
    from shared.providers.factory import get_tts_provider
    provider = get_tts_provider()
    voices = await provider.list_voices()
    return [VoicePreset(**v) for v in voices]
