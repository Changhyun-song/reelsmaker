"""Worker handler for TTS generation (shot-level narration).

Flow:
  1. Load shot narration text
  2. Call TTS provider
  3. Upload audio to S3
  4. Create Asset + VoiceTrack + ProviderRun rows
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from shared.database import async_session_factory
from shared.models.asset import Asset
from shared.models.provider_run import ProviderRun
from shared.models.shot import Shot
from shared.models.voice_track import VoiceTrack
from shared.providers.factory import get_tts_provider
from shared.providers.tts_base import TTSRequest
from shared.storage import ensure_bucket, generate_storage_key, upload_bytes

logger = logging.getLogger("reelsmaker.worker.tts")


async def _update_job_progress(job_id: str, progress: int) -> None:
    from worker.main import _update_job
    await _update_job(job_id, progress=progress)


async def handle_tts_generate(
    job_id: str,
    project_id: str,
    shot_id: str,
    voice_id: str = "narrator-ko-male",
    language: str = "ko",
    speed: float = 1.0,
    emotion: str = "",
    speaker_name: str = "",
    text_override: str | None = None,
    **_params,
) -> dict:
    """Generate TTS audio for a shot's narration segment.

    1. Load shot narration_segment (or use text_override)
    2. Call TTS provider
    3. Upload audio to S3
    4. Create Asset + VoiceTrack + ProviderRun
    """
    pid = uuid.UUID(project_id)
    sid = uuid.UUID(shot_id)

    ensure_bucket()
    await _update_job_progress(job_id, 5)

    # 1. Resolve text
    text = text_override
    if not text:
        async with async_session_factory() as session:
            shot = (
                await session.execute(select(Shot).where(Shot.id == sid))
            ).scalar_one_or_none()
            if not shot:
                raise ValueError(f"Shot {shot_id} not found")
            text = shot.narration_segment

    if not text or not text.strip():
        raise ValueError(f"Shot {shot_id} has no narration text")

    await _update_job_progress(job_id, 15)

    logger.info(
        "tts_generate shot=%s voice=%s text_len=%d",
        shot_id, voice_id, len(text),
    )

    # 2. Call TTS provider
    provider = get_tts_provider()
    request = TTSRequest(
        text=text.strip(),
        voice_id=voice_id,
        language=language,
        speed=speed,
        emotion=emotion,
        speaker_name=speaker_name,
    )

    response = await provider.generate(request)
    await _update_job_progress(job_id, 60)

    # 3. Upload audio to S3
    storage_key = generate_storage_key(
        project_id=pid,
        parent_type="shot",
        parent_id=sid,
        variant_index=0,
        extension="mp3",
    )
    upload_bytes(storage_key, response.audio_bytes, content_type=response.mime_type)
    await _update_job_progress(job_id, 75)

    # 4. Create records
    async with async_session_factory() as session:
        # ProviderRun
        provider_run = ProviderRun(
            project_id=pid,
            provider=response.provider,
            operation="tts_generate",
            model=response.model,
            input_params={
                "text": text[:300],
                "voice_id": voice_id,
                "language": language,
                "speed": speed,
                "emotion": emotion,
            },
            output_summary={
                "duration_ms": response.duration_ms,
                "sample_rate": response.sample_rate,
                "word_count": len(response.word_timestamps),
                "file_size": len(response.audio_bytes),
            },
            status="completed",
            latency_ms=response.latency_ms,
            cost_estimate=response.cost_estimate,
        )
        session.add(provider_run)
        await session.flush()
        await session.refresh(provider_run)

        # Asset
        asset = Asset(
            project_id=pid,
            parent_type="shot",
            parent_id=sid,
            asset_type="audio_tts",
            storage_key=storage_key,
            filename=storage_key.split("/")[-1],
            mime_type=response.mime_type,
            file_size_bytes=len(response.audio_bytes),
            metadata_={
                "duration_ms": response.duration_ms,
                "sample_rate": response.sample_rate,
                "voice_id": voice_id,
                "language": language,
                "speed": speed,
                "provider": response.provider,
                "model": response.model,
            },
            version=1,
            provider_run_id=provider_run.id,
            status="ready",
        )
        session.add(asset)
        await session.flush()
        await session.refresh(asset)

        # Serialize word timestamps
        ts_data = [
            {"word": wt.word, "start_ms": wt.start_ms, "end_ms": wt.end_ms}
            for wt in response.word_timestamps
        ]

        # VoiceTrack
        voice_track = VoiceTrack(
            project_id=pid,
            shot_id=sid,
            text=text.strip(),
            voice_id=voice_id,
            speaker_name=speaker_name or None,
            language=language,
            speed=speed,
            emotion=emotion or None,
            asset_id=asset.id,
            provider_run_id=provider_run.id,
            duration_ms=response.duration_ms,
            timestamps={"words": ts_data} if ts_data else None,
            tts_metadata={
                "sample_rate": response.sample_rate,
                "provider": response.provider,
                "model": response.model,
            },
            status="ready",
        )
        session.add(voice_track)
        await session.flush()
        await session.refresh(voice_track)

        await session.commit()

        voice_track_id = str(voice_track.id)
        asset_id = str(asset.id)

    await _update_job_progress(job_id, 100)

    logger.info(
        "tts_generate completed: shot=%s voice_track=%s duration=%dms",
        shot_id, voice_track_id, response.duration_ms,
    )

    return {
        "shot_id": shot_id,
        "voice_track_id": voice_track_id,
        "asset_id": asset_id,
        "duration_ms": response.duration_ms,
        "voice_id": voice_id,
        "provider": response.provider,
    }
