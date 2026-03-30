"""Worker handler for final video rendering.

Flow:
  1. Load Timeline + RenderJob from DB
  2. Download all referenced assets from S3 to temp dir
  3. Build ffmpeg command
  4. Run ffmpeg subprocess
  5. Upload output mp4 to S3
  6. Create output Asset, update RenderJob
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from shared.database import async_session_factory
from shared.models.asset import Asset
from shared.models.render_job import RenderJob
from shared.models.subtitle_track import SubtitleTrack
from shared.models.timeline import Timeline
from shared.render.ffmpeg_builder import (
    RenderConfig,
    SegmentFile,
    build_render_command,
    probe_file,
)
from shared.storage import (
    download_to_file,
    ensure_bucket,
    generate_storage_key,
    get_presigned_url,
    upload_file,
)

logger = logging.getLogger("reelsmaker.worker.render")


async def _update_job_progress(job_id: str, progress: int) -> None:
    from worker.main import _update_job
    await _update_job(job_id, progress=progress)


async def _update_render_job(
    render_job_id: uuid.UUID,
    status: str | None = None,
    progress: int | None = None,
    ffmpeg_command: str | None = None,
    error_message: str | None = None,
    output_asset_id: uuid.UUID | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    async with async_session_factory() as session:
        rj = await session.get(RenderJob, render_job_id)
        if not rj:
            return
        if status:
            rj.status = status
        if progress is not None:
            rj.progress = progress
        if ffmpeg_command:
            rj.ffmpeg_command = ffmpeg_command
        if error_message is not None:
            rj.error_message = error_message
        if output_asset_id:
            rj.output_asset_id = output_asset_id
        if started_at:
            rj.started_at = started_at
        if completed_at:
            rj.completed_at = completed_at
        await session.commit()


def _download_asset_to_dir(storage_key: str, tmp_dir: str, label: str) -> str:
    """Download an S3 object to a local temp file."""
    ext = storage_key.rsplit(".", 1)[-1] if "." in storage_key else "bin"
    local_path = os.path.join(tmp_dir, f"{label}.{ext}")
    download_to_file(storage_key, local_path)
    return local_path


async def handle_render_final(
    job_id: str,
    project_id: str,
    timeline_id: str,
    render_job_id: str,
    burn_subtitles: bool = False,
    **_params,
) -> dict:
    pid = uuid.UUID(project_id)
    tlid = uuid.UUID(timeline_id)
    rjid = uuid.UUID(render_job_id)

    ensure_bucket()
    await _update_job_progress(job_id, 2)
    await _update_render_job(rjid, status="rendering", started_at=datetime.now(timezone.utc))

    # 1. Load timeline
    async with async_session_factory() as session:
        tl = await session.get(Timeline, tlid)
        if not tl or not tl.segments:
            raise ValueError(f"Timeline {timeline_id} not found or has no segments")

        segments_data = tl.segments
        sub_track_id = tl.subtitle_track_id

    video_segs = segments_data.get("video_segments", [])
    audio_segs = segments_data.get("audio_segments", [])
    pause_segs = segments_data.get("pause_segments", [])
    out_settings = segments_data.get("output_settings", {})
    intro_fade_in_ms = segments_data.get("intro_fade_in_ms", 0)
    outro_fade_out_ms = segments_data.get("outro_fade_out_ms", 0)
    format_profile = segments_data.get("format_profile", "shorts")

    if not video_segs:
        raise ValueError("No video segments in timeline")

    audio_map = {a["shot_id"]: a for a in audio_segs}
    pause_after_map: dict[str, dict] = {}
    for ps in pause_segs:
        after_id = ps.get("after_shot_id")
        if after_id:
            pause_after_map[after_id] = ps

    await _update_job_progress(job_id, 8)
    logger.info(
        "render: %d video, %d pause segments, format=%s, timeline=%s",
        len(video_segs), len(pause_segs), format_profile, timeline_id,
    )

    # 2. Download assets to temp dir
    tmp_dir = tempfile.mkdtemp(prefix="reelsmaker_render_")
    try:
        segment_files: list[SegmentFile] = []
        seg_counter = 0
        total_video_segs = len(video_segs)

        for vs_idx, vs in enumerate(video_segs):
            asset_type = vs.get("asset_type", "missing")
            storage_key = vs.get("storage_key")
            duration_ms = vs.get("duration_ms", 4000)
            is_first = vs_idx == 0
            is_last = vs_idx == total_video_segs - 1

            video_path = None
            image_path = None

            if asset_type == "video" and storage_key:
                try:
                    video_path = _download_asset_to_dir(storage_key, tmp_dir, f"video_{seg_counter}")
                    probe = probe_file(video_path)
                    if not probe.get("streams"):
                        logger.warning("Probe returned no streams for segment %d", seg_counter)
                except Exception as e:
                    logger.error("Failed to download video for segment %d: %s", seg_counter, e)
                    asset_type = "missing"

            elif asset_type == "image" and storage_key:
                try:
                    image_path = _download_asset_to_dir(storage_key, tmp_dir, f"image_{seg_counter}")
                except Exception as e:
                    logger.error("Failed to download image for segment %d: %s", seg_counter, e)
                    asset_type = "missing"

            # Audio
            audio_path = None
            shot_id = vs.get("shot_id", "")
            audio_info = audio_map.get(shot_id, {})
            audio_storage_key = audio_info.get("storage_key")
            if audio_storage_key and audio_info.get("status") == "ready":
                try:
                    audio_path = _download_asset_to_dir(audio_storage_key, tmp_dir, f"audio_{seg_counter}")
                except Exception as e:
                    logger.warning("Failed to download audio for segment %d: %s", seg_counter, e)

            # Ken Burns params (v2 with easing)
            im = vs.get("image_motion") or {}
            zoom_start = im.get("zoom_start", 1.0)
            zoom_end = im.get("zoom_end", 1.15)
            pan_direction = im.get("pan_direction", "left_to_right")
            easing = im.get("easing", "linear")

            segment_files.append(SegmentFile(
                index=seg_counter,
                asset_type=asset_type,
                video_path=video_path,
                image_path=image_path,
                audio_path=audio_path,
                duration_ms=duration_ms,
                zoom_start=zoom_start,
                zoom_end=zoom_end,
                pan_direction=pan_direction,
                easing=easing,
                is_first=is_first,
                is_last=is_last,
                fade_in_ms=intro_fade_in_ms if is_first else 0,
                fade_out_ms=outro_fade_out_ms if is_last else 0,
            ))
            seg_counter += 1

            # Insert pause segment after this shot if exists
            pause_info = pause_after_map.get(shot_id)
            if pause_info and pause_info.get("duration_ms", 0) > 0:
                pause_dur = pause_info["duration_ms"]
                pause_visual = pause_info.get("visual", "black")
                segment_files.append(SegmentFile(
                    index=seg_counter,
                    asset_type="pause",
                    duration_ms=pause_dur,
                    pause_visual=pause_visual,
                ))
                seg_counter += 1

        await _update_job_progress(job_id, 30)
        await _update_render_job(rjid, progress=30)

        # 3. Download subtitle if burn-in requested
        subtitle_path = None
        if burn_subtitles and sub_track_id:
            async with async_session_factory() as session:
                sub = await session.get(SubtitleTrack, sub_track_id)
                if sub and sub.content:
                    subtitle_path = os.path.join(tmp_dir, f"subtitles.{sub.format or 'srt'}")
                    with open(subtitle_path, "w", encoding="utf-8") as f:
                        f.write(sub.content)

        # 4. Build ffmpeg command
        output_path = os.path.join(tmp_dir, "output.mp4")

        render_cfg = RenderConfig(
            width=out_settings.get("width", 1080),
            height=out_settings.get("height", 1920),
            fps=out_settings.get("fps", 30),
            subtitle_path=subtitle_path,
            burn_subtitles=burn_subtitles and subtitle_path is not None,
            intro_fade_in_ms=intro_fade_in_ms,
            outro_fade_out_ms=outro_fade_out_ms,
        )

        cmd = build_render_command(segment_files, output_path, render_cfg)
        cmd_str = " ".join(cmd)
        logger.info("ffmpeg command (truncated): %s", cmd_str[:500])

        await _update_render_job(rjid, ffmpeg_command=cmd_str, progress=35)
        await _update_job_progress(job_id, 35)

        # 5. Run ffmpeg
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "")[-2000:]
            logger.error("ffmpeg failed: %s", stderr_tail)
            await _update_render_job(
                rjid,
                status="failed",
                error_message=f"ffmpeg exit code {proc.returncode}: {stderr_tail[:1000]}",
                completed_at=datetime.now(timezone.utc),
            )
            raise RuntimeError(f"ffmpeg failed with exit code {proc.returncode}")

        if not os.path.exists(output_path):
            await _update_render_job(
                rjid,
                status="failed",
                error_message="Output file was not created",
                completed_at=datetime.now(timezone.utc),
            )
            raise RuntimeError("ffmpeg did not produce output file")

        await _update_job_progress(job_id, 75)
        await _update_render_job(rjid, progress=75)

        # 6. Probe output
        out_probe = probe_file(output_path)
        out_size = os.path.getsize(output_path)
        out_duration_sec = 0.0
        if out_probe.get("format"):
            out_duration_sec = float(out_probe["format"].get("duration", 0))

        # 7. Upload to S3
        storage_key = generate_storage_key(
            project_id=pid,
            parent_type="render",
            parent_id=tlid,
            variant_index=0,
            extension="mp4",
        )
        upload_file(storage_key, output_path, content_type="video/mp4")

        await _update_job_progress(job_id, 90)
        await _update_render_job(rjid, progress=90)

        # 8. Create Asset + update RenderJob
        async with async_session_factory() as session:
            asset = Asset(
                project_id=pid,
                parent_type="timeline",
                parent_id=tlid,
                asset_type="render",
                storage_key=storage_key,
                filename=storage_key.split("/")[-1],
                mime_type="video/mp4",
                file_size_bytes=out_size,
                metadata_={
                    "duration_sec": out_duration_sec,
                    "width": render_cfg.width,
                    "height": render_cfg.height,
                    "fps": render_cfg.fps,
                    "codec": render_cfg.video_codec,
                    "burn_subtitles": burn_subtitles,
                    "segments_count": len(segment_files),
                },
                version=1,
                status="ready",
            )
            session.add(asset)
            await session.flush()
            await session.refresh(asset)
            asset_id = asset.id
            await session.commit()

        await _update_render_job(
            rjid,
            status="completed",
            progress=100,
            output_asset_id=asset_id,
            completed_at=datetime.now(timezone.utc),
        )
        await _update_job_progress(job_id, 100)

        logger.info(
            "render completed: render_job=%s output=%s size=%d duration=%.1fs",
            render_job_id, storage_key, out_size, out_duration_sec,
        )

        return {
            "render_job_id": render_job_id,
            "asset_id": str(asset_id),
            "storage_key": storage_key,
            "file_size_bytes": out_size,
            "duration_sec": out_duration_sec,
        }

    finally:
        # Cleanup temp dir
        import shutil
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
