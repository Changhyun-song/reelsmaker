"""Worker handler for timeline composition.

Flow:
  1. Load all scenes/shots for a ScriptVersion (ordered)
  2. For each shot, find latest ready video/image/voice assets
  3. Find latest subtitle track for the script version
  4. Call compose_timeline() to build TimelineData
  5. Upsert Timeline row
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.models.asset import Asset
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.models.subtitle_track import SubtitleTrack
from shared.models.timeline import Timeline
from shared.models.voice_track import VoiceTrack
from shared.schemas.timeline import TimelineData
from shared.timeline.composer import ComposerConfig, ShotInput, compose_timeline

logger = logging.getLogger("reelsmaker.worker.timeline")


async def _update_job_progress(job_id: str, progress: int) -> None:
    from worker.main import _update_job
    await _update_job(job_id, progress=progress)


async def _find_best_asset(
    session: AsyncSession,
    parent_type: str,
    parent_id: uuid.UUID,
    asset_type: str,
) -> Asset | None:
    """Find the best asset: prefer explicitly selected, then latest ready."""
    selected = await session.execute(
        select(Asset)
        .where(
            Asset.parent_type == parent_type,
            Asset.parent_id == parent_id,
            Asset.asset_type == asset_type,
            Asset.status == "ready",
            Asset.is_selected == True,  # noqa: E712
        )
        .limit(1)
    )
    asset = selected.scalar_one_or_none()
    if asset:
        return asset

    result = await session.execute(
        select(Asset)
        .where(
            Asset.parent_type == parent_type,
            Asset.parent_id == parent_id,
            Asset.asset_type == asset_type,
            Asset.status == "ready",
        )
        .order_by(Asset.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _find_best_voice_track(
    session: AsyncSession,
    shot_id: uuid.UUID,
) -> VoiceTrack | None:
    """Find the best voice track: prefer explicitly selected, then latest ready."""
    selected = await session.execute(
        select(VoiceTrack)
        .where(
            VoiceTrack.shot_id == shot_id,
            VoiceTrack.status == "ready",
            VoiceTrack.is_selected == True,  # noqa: E712
        )
        .limit(1)
    )
    track = selected.scalar_one_or_none()
    if track:
        return track

    result = await session.execute(
        select(VoiceTrack)
        .where(
            VoiceTrack.shot_id == shot_id,
            VoiceTrack.status == "ready",
        )
        .order_by(VoiceTrack.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _find_best_subtitle_track(
    session: AsyncSession,
    script_version_id: uuid.UUID,
) -> SubtitleTrack | None:
    result = await session.execute(
        select(SubtitleTrack)
        .where(
            SubtitleTrack.script_version_id == script_version_id,
            SubtitleTrack.status == "ready",
        )
        .order_by(SubtitleTrack.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def handle_timeline_compose(
    job_id: str,
    project_id: str,
    script_version_id: str,
    output_width: int = 1080,
    output_height: int = 1920,
    output_fps: int = 30,
    format_name: str = "shorts",
    **_params,
) -> dict:
    pid = uuid.UUID(project_id)
    svid = uuid.UUID(script_version_id)

    await _update_job_progress(job_id, 5)

    # 1. Load scenes & shots
    async with async_session_factory() as session:
        scenes_result = await session.execute(
            select(Scene)
            .where(Scene.script_version_id == svid)
            .order_by(Scene.order_index)
        )
        scenes = list(scenes_result.scalars().all())
        if not scenes:
            raise ValueError(f"No scenes found for script_version {script_version_id}")

        scene_ids = [s.id for s in scenes]
        scene_order_map = {s.id: s.order_index for s in scenes}

        shots_result = await session.execute(
            select(Shot)
            .where(Shot.scene_id.in_(scene_ids))
            .order_by(Shot.scene_id, Shot.order_index)
        )
        shots = list(shots_result.scalars().all())
        if not shots:
            raise ValueError("No shots found")

    await _update_job_progress(job_id, 15)
    logger.info("timeline_compose: %d scenes, %d shots", len(scenes), len(shots))

    # 2. For each shot, resolve assets
    shot_inputs: list[ShotInput] = []

    async with async_session_factory() as session:
        for shot in shots:
            # Video asset (shot level)
            video_asset = await _find_best_asset(session, "shot", shot.id, "video")
            video_asset_id = str(video_asset.id) if video_asset else None
            video_storage_key = video_asset.storage_key if video_asset else None
            video_duration_ms = None
            if video_asset and video_asset.metadata_:
                dur_sec = video_asset.metadata_.get("duration_sec")
                if dur_sec:
                    video_duration_ms = int(float(dur_sec) * 1000)

            # Image asset (frame_spec level — find any ready start frame image)
            image_asset = await _find_best_asset(session, "shot", shot.id, "image")
            if not image_asset:
                image_asset = await _find_best_asset(session, "frame_spec", shot.id, "image")
            image_asset_id = str(image_asset.id) if image_asset else None
            image_storage_key = image_asset.storage_key if image_asset else None

            # If no shot-level image, try to find any frame_spec image
            if not image_asset_id:
                from shared.models.frame_spec import FrameSpec
                fs_result = await session.execute(
                    select(FrameSpec.id)
                    .where(FrameSpec.shot_id == shot.id)
                    .order_by(FrameSpec.order_index)
                )
                frame_ids = [r[0] for r in fs_result.all()]
                for fid in frame_ids:
                    img = await _find_best_asset(session, "frame_spec", fid, "image")
                    if img:
                        image_asset_id = str(img.id)
                        image_storage_key = img.storage_key
                        break

            # Voice track
            vt = await _find_best_voice_track(session, shot.id)
            voice_track_id = str(vt.id) if vt else None
            voice_asset_id = str(vt.asset_id) if vt and vt.asset_id else None
            voice_storage_key = None
            voice_duration_ms = vt.duration_ms if vt else None
            voice_id_str = vt.voice_id if vt else None
            if vt and vt.asset_id:
                va = await session.get(Asset, vt.asset_id)
                if va:
                    voice_storage_key = va.storage_key

            shot_inputs.append(ShotInput(
                shot_id=str(shot.id),
                scene_id=str(shot.scene_id),
                order_index=shot.order_index,
                scene_order_index=scene_order_map.get(shot.scene_id, 0),
                duration_sec=shot.duration_sec,
                shot_type=shot.shot_type,
                camera_movement=shot.camera_movement,
                asset_strategy=shot.asset_strategy,
                transition_in=shot.transition_in,
                transition_out=shot.transition_out,
                narration_segment=shot.narration_segment,
                video_asset_id=video_asset_id,
                video_storage_key=video_storage_key,
                video_duration_ms=video_duration_ms,
                image_asset_id=image_asset_id,
                image_storage_key=image_storage_key,
                voice_track_id=voice_track_id,
                voice_asset_id=voice_asset_id,
                voice_storage_key=voice_storage_key,
                voice_duration_ms=voice_duration_ms,
                voice_id=voice_id_str,
            ))

    await _update_job_progress(job_id, 55)

    # 3. Find subtitle track
    async with async_session_factory() as session:
        sub_track = await _find_best_subtitle_track(session, svid)
    subtitle_track_id = str(sub_track.id) if sub_track else None

    await _update_job_progress(job_id, 65)

    # 4. Compose timeline with editing rules
    config = ComposerConfig(
        output_width=output_width,
        output_height=output_height,
        output_fps=output_fps,
        format_name=format_name,
    )
    timeline_data: TimelineData = compose_timeline(
        shots=shot_inputs,
        subtitle_track_id=subtitle_track_id,
        config=config,
    )

    await _update_job_progress(job_id, 80)

    # 5. Upsert Timeline row
    async with async_session_factory() as session:
        existing = (
            await session.execute(
                select(Timeline)
                .where(
                    Timeline.project_id == pid,
                    Timeline.script_version_id == svid,
                )
                .order_by(Timeline.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        tl_data_dict = timeline_data.model_dump(mode="json")

        if existing:
            existing.segments = tl_data_dict
            existing.total_duration_ms = timeline_data.total_duration_ms
            existing.subtitle_track_id = sub_track.id if sub_track else None
            existing.status = "composed"
            await session.flush()
            await session.refresh(existing)
            timeline_id = str(existing.id)
        else:
            tl = Timeline(
                project_id=pid,
                script_version_id=svid,
                total_duration_ms=timeline_data.total_duration_ms,
                segments=tl_data_dict,
                subtitle_track_id=sub_track.id if sub_track else None,
                status="composed",
            )
            session.add(tl)
            await session.flush()
            await session.refresh(tl)
            timeline_id = str(tl.id)

        await session.commit()

    await _update_job_progress(job_id, 100)

    logger.info(
        "timeline_compose completed: timeline=%s total=%dms segments=%d warnings=%d",
        timeline_id, timeline_data.total_duration_ms,
        len(timeline_data.video_segments), len(timeline_data.warnings),
    )

    return {
        "timeline_id": timeline_id,
        "total_duration_ms": timeline_data.total_duration_ms,
        "total_segments": len(timeline_data.video_segments),
        "warnings_count": len(timeline_data.warnings),
    }
