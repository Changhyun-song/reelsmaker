"""Worker handler for subtitle generation.

Flow:
  1. Collect all shots (ordered) from a ScriptVersion's scenes
  2. For each shot, load narration text + VoiceTrack word timestamps (if any)
  3. Resolve unified timeline of word timings
  4. Segment into subtitle cues with style rules
  5. Format as SRT, upload to S3
  6. Create SubtitleTrack + Asset records
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.database import async_session_factory
from shared.models.asset import Asset
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.models.subtitle_track import SubtitleTrack
from shared.models.voice_track import VoiceTrack
from shared.storage import ensure_bucket, generate_storage_key, upload_bytes
from shared.subtitle.formatter import segments_to_srt, segments_to_vtt
from shared.subtitle.segmenter import SegmenterConfig, build_segments
from shared.subtitle.timing import ShotNarration, WordTiming, resolve_timing

logger = logging.getLogger("reelsmaker.worker.subtitle")


async def _update_job_progress(job_id: str, progress: int) -> None:
    from worker.main import _update_job
    await _update_job(job_id, progress=progress)


def _parse_voice_track_timestamps(vt: VoiceTrack) -> list[WordTiming] | None:
    """Extract WordTiming list from VoiceTrack.timestamps JSON."""
    if not vt.timestamps:
        return None
    words = vt.timestamps.get("words")
    if not words or not isinstance(words, list):
        return None
    return [
        WordTiming(word=w["word"], start_ms=w["start_ms"], end_ms=w["end_ms"])
        for w in words
        if "word" in w and "start_ms" in w and "end_ms" in w
    ]


async def handle_subtitle_generate(
    job_id: str,
    project_id: str,
    script_version_id: str,
    format: str = "srt",
    language: str = "ko",
    max_chars_per_line: int = 35,
    max_lines: int = 2,
    line_break_strategy: str = "word",
    gap_ms: int = 100,
    min_segment_ms: int = 500,
    max_segment_ms: int = 6000,
    **_params,
) -> dict:
    pid = uuid.UUID(project_id)
    svid = uuid.UUID(script_version_id)

    ensure_bucket()
    await _update_job_progress(job_id, 5)

    # 1. Collect shots from all scenes of the script version
    async with async_session_factory() as session:
        scenes_result = await session.execute(
            select(Scene)
            .where(Scene.script_version_id == svid)
            .order_by(Scene.order_index)
        )
        scenes = list(scenes_result.scalars().all())
        if not scenes:
            raise ValueError(f"No scenes for script_version {script_version_id}")

        scene_ids = [s.id for s in scenes]

        shots_result = await session.execute(
            select(Shot)
            .where(Shot.scene_id.in_(scene_ids))
            .order_by(Shot.scene_id, Shot.order_index)
        )
        shots = list(shots_result.scalars().all())

    await _update_job_progress(job_id, 20)

    # 2. Build ShotNarration objects with optional TTS word timestamps
    narrations: list[ShotNarration] = []
    global_order = 0

    # Build scene order map for global shot ordering
    scene_order = {s.id: s.order_index for s in scenes}

    shots_sorted = sorted(shots, key=lambda s: (scene_order.get(s.scene_id, 0), s.order_index))

    async with async_session_factory() as session:
        for shot in shots_sorted:
            if not shot.narration_segment or not shot.narration_segment.strip():
                global_order += 1
                continue

            vt_result = await session.execute(
                select(VoiceTrack)
                .where(
                    VoiceTrack.shot_id == shot.id,
                    VoiceTrack.status == "ready",
                )
                .order_by(VoiceTrack.created_at.desc())
                .limit(1)
            )
            voice_track = vt_result.scalar_one_or_none()

            word_timestamps = None
            if voice_track:
                word_timestamps = _parse_voice_track_timestamps(voice_track)

            narrations.append(ShotNarration(
                shot_id=str(shot.id),
                text=shot.narration_segment.strip(),
                order_index=global_order,
                duration_sec=shot.duration_sec,
                word_timestamps=word_timestamps,
                speaker=voice_track.speaker_name if voice_track else None,
            ))
            global_order += 1

    if not narrations:
        raise ValueError("No narration text found in any shot")

    await _update_job_progress(job_id, 40)
    logger.info("subtitle_generate: %d narration segments collected", len(narrations))

    # 3. Resolve timing
    word_timings, timing_source = resolve_timing(narrations, gap_between_shots_ms=200)
    await _update_job_progress(job_id, 55)

    # 4. Segment into cues
    config = SegmenterConfig(
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
        gap_ms=gap_ms,
        min_segment_ms=min_segment_ms,
        max_segment_ms=max_segment_ms,
        line_break_strategy=line_break_strategy,
    )
    cues = build_segments(word_timings, config)
    await _update_job_progress(job_id, 70)

    # 5. Format
    if format == "vtt":
        content_str = segments_to_vtt(cues)
        mime = "text/vtt"
        ext = "vtt"
    else:
        content_str = segments_to_srt(cues)
        mime = "text/srt"
        ext = "srt"

    content_bytes = content_str.encode("utf-8")
    total_duration_ms = cues[-1].end_ms if cues else 0

    # 6. Upload to S3
    storage_key = generate_storage_key(
        project_id=pid,
        parent_type="subtitle",
        parent_id=svid,
        variant_index=0,
        extension=ext,
    )
    upload_bytes(storage_key, content_bytes, content_type=mime)
    await _update_job_progress(job_id, 85)

    # 7. Create records
    segments_json = [
        {
            "index": c.index,
            "start_ms": c.start_ms,
            "end_ms": c.end_ms,
            "text": c.text,
            "shot_id": c.shot_id,
            "speaker": c.speaker,
        }
        for c in cues
    ]

    async with async_session_factory() as session:
        asset = Asset(
            project_id=pid,
            parent_type="script_version",
            parent_id=svid,
            asset_type="subtitle",
            storage_key=storage_key,
            filename=storage_key.split("/")[-1],
            mime_type=mime,
            file_size_bytes=len(content_bytes),
            metadata_={
                "format": ext,
                "total_segments": len(cues),
                "total_duration_ms": total_duration_ms,
                "timing_source": timing_source,
                "language": language,
            },
            version=1,
            status="ready",
        )
        session.add(asset)
        await session.flush()
        await session.refresh(asset)

        track = SubtitleTrack(
            project_id=pid,
            script_version_id=svid,
            language=language,
            format=ext,
            timing_source=timing_source,
            segments=segments_json,
            style_settings={
                "max_chars_per_line": max_chars_per_line,
                "max_lines": max_lines,
                "line_break_strategy": line_break_strategy,
                "gap_ms": gap_ms,
                "min_segment_ms": min_segment_ms,
                "max_segment_ms": max_segment_ms,
            },
            content=content_str,
            total_segments=len(cues),
            total_duration_ms=total_duration_ms,
            asset_id=asset.id,
            status="ready",
        )
        session.add(track)
        await session.flush()
        await session.refresh(track)
        await session.commit()

        track_id = str(track.id)
        asset_id = str(asset.id)

    await _update_job_progress(job_id, 100)

    logger.info(
        "subtitle_generate completed: track=%s segments=%d duration=%dms timing=%s",
        track_id, len(cues), total_duration_ms, timing_source,
    )

    return {
        "subtitle_track_id": track_id,
        "asset_id": asset_id,
        "total_segments": len(cues),
        "total_duration_ms": total_duration_ms,
        "timing_source": timing_source,
        "format": ext,
    }
