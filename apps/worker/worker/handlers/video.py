"""Worker handler for shot-level video clip generation.

Flow:
  1. Load shot + compile video prompt
  2. Optionally fetch start/end frame image assets from S3 (prefer is_selected)
  3. Call VideoProvider N times for multi-variant
  4. Upload resulting MP4s to S3
  5. Create Asset + ProviderRun rows (non-destructive)
  6. Update Shot status
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select

from shared.database import async_session_factory
from shared.models.asset import Asset
from shared.models.frame_spec import FrameSpec
from shared.models.provider_run import ProviderRun
from shared.models.shot import Shot
from shared.prompt_compiler import compile_full
from shared.prompt_compiler.context_builder import build_shot_compiler_context
from shared.providers.factory import get_video_provider
from shared.providers.video_base import VideoGenerationRequest
from shared.storage import ensure_bucket, generate_storage_key, upload_bytes

logger = logging.getLogger("reelsmaker.worker.video")


async def _update_job_progress(job_id: str, progress: int) -> None:
    from worker.main import _update_job
    await _update_job(job_id, progress=progress)


def _download_s3_bytes(storage_key: str) -> bytes | None:
    try:
        from shared.storage import _get_client, _bucket
        response = _get_client().get_object(Bucket=_bucket(), Key=storage_key)
        return response["Body"].read()
    except Exception:
        return None


async def _find_frame_asset(
    shot_id: uuid.UUID,
    frame_role: str,
    db,
) -> Asset | None:
    """Find the best image asset for a frame role. Prefers is_selected, then latest."""
    frame = (
        await db.execute(
            select(FrameSpec)
            .where(FrameSpec.shot_id == shot_id, FrameSpec.frame_role == frame_role)
            .order_by(FrameSpec.order_index)
            .limit(1)
        )
    ).scalar_one_or_none()
    if not frame:
        return None

    # Prefer selected asset
    selected = (
        await db.execute(
            select(Asset)
            .where(
                Asset.parent_type == "frame_spec",
                Asset.parent_id == frame.id,
                Asset.asset_type == "image",
                Asset.status == "ready",
                Asset.is_selected.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if selected:
        return selected

    # Fallback to most recent
    return (
        await db.execute(
            select(Asset)
            .where(
                Asset.parent_type == "frame_spec",
                Asset.parent_id == frame.id,
                Asset.asset_type == "image",
                Asset.status == "ready",
            )
            .order_by(Asset.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _next_version(shot_id: uuid.UUID) -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.coalesce(func.max(Asset.version), 0))
            .where(
                Asset.parent_type == "shot",
                Asset.parent_id == shot_id,
                Asset.asset_type == "video",
            )
        )
        return (result.scalar() or 0) + 1


async def handle_video_generate(
    job_id: str,
    project_id: str,
    shot_id: str,
    mode: str = "auto",
    duration_override: float | None = None,
    num_variants: int = 1,
    **_params,
) -> dict:
    """Generate video clip(s) for a single Shot.

    Non-destructive: existing video assets are preserved. New assets get
    incremented version numbers and a unique generation_batch ID.

    Modes:
      - "image_to_video": use selected start/end frame images as reference
      - "text_to_video": use only the compiled video prompt
      - "auto": use image_to_video if frame images exist, else text_to_video
    """
    pid = uuid.UUID(project_id)
    sid = uuid.UUID(shot_id)
    num_variants = max(1, min(num_variants, 3))
    batch_id = f"vid-{uuid.uuid4().hex[:12]}"

    ensure_bucket()
    await _update_job_progress(job_id, 5)

    # 1. Compile video prompt + load context
    async with async_session_factory() as session:
        ctx = await build_shot_compiler_context(pid, sid, session)

        shot = (
            await session.execute(select(Shot).where(Shot.id == sid))
        ).scalar_one_or_none()
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        duration = duration_override or shot.duration_sec or 4.0

        # 2. Try to load selected start/end frame images
        start_asset = await _find_frame_asset(sid, "start", session)
        end_asset = await _find_frame_asset(sid, "end", session)

    compiled = compile_full(ctx)
    next_ver = await _next_version(sid)
    await _update_job_progress(job_id, 15)

    # Determine effective mode
    effective_mode = mode
    if mode == "auto":
        effective_mode = "image_to_video" if start_asset else "text_to_video"

    logger.info(
        "video_generate shot=%s batch=%s mode=%s variants=%d has_start=%s has_end=%s",
        shot_id, batch_id, effective_mode, num_variants,
        start_asset is not None, end_asset is not None,
    )

    # 3. Download frame images if image_to_video
    start_bytes: bytes | None = None
    end_bytes: bytes | None = None

    if effective_mode == "image_to_video":
        if start_asset and start_asset.storage_key:
            start_bytes = _download_s3_bytes(start_asset.storage_key)
        if end_asset and end_asset.storage_key:
            end_bytes = _download_s3_bytes(end_asset.storage_key)

        if not start_bytes:
            effective_mode = "text_to_video"
            logger.warning("No start frame image found, falling back to text_to_video")

    await _update_job_progress(job_id, 20)

    # 4. Generate N variants
    provider = get_video_provider()
    asset_ids: list[str] = []
    progress_per_variant = 60 // max(num_variants, 1)

    async with async_session_factory() as session:
        for vi in range(num_variants):
            variant_ver = next_ver + vi

            request = VideoGenerationRequest(
                prompt=compiled.video_prompt,
                negative_prompt=compiled.negative_prompt,
                mode=effective_mode,
                start_frame_bytes=start_bytes,
                end_frame_bytes=end_bytes,
                duration_sec=duration,
                width=ctx.project.width,
                height=ctx.project.height,
                aspect_ratio=ctx.project.aspect_ratio,
                fps=30,
                provider_options={
                    **compiled.provider_options,
                    "variant_index": vi,
                    "batch_id": batch_id,
                },
            )

            try:
                response = await provider.generate(request)
            except Exception as exc:
                logger.error("video variant %d failed: %s", vi, exc)
                continue

            video = response.video
            storage_key = generate_storage_key(
                project_id=pid,
                parent_type="shot",
                parent_id=sid,
                variant_index=variant_ver,
                extension="mp4",
            )
            upload_bytes(storage_key, video.video_bytes, content_type=video.mime_type)

            provider_run = ProviderRun(
                project_id=pid,
                provider=response.provider,
                operation="video_generate",
                model=response.model,
                input_params={
                    "prompt": compiled.video_prompt[:500],
                    "mode": effective_mode,
                    "duration_sec": duration,
                    "variant_index": vi,
                    "batch_id": batch_id,
                    "has_start_frame": start_bytes is not None,
                    "has_end_frame": end_bytes is not None,
                },
                output_summary={
                    "duration_sec": video.duration_sec,
                    "fps": video.fps,
                    "width": video.width,
                    "height": video.height,
                    "file_size": len(video.video_bytes),
                    "latency_ms": response.latency_ms,
                },
                status="completed",
                latency_ms=response.latency_ms,
                cost_estimate=response.cost_estimate,
            )
            session.add(provider_run)
            await session.flush()
            await session.refresh(provider_run)

            asset = Asset(
                project_id=pid,
                parent_type="shot",
                parent_id=sid,
                asset_type="video",
                storage_key=storage_key,
                filename=storage_key.split("/")[-1],
                mime_type=video.mime_type,
                file_size_bytes=len(video.video_bytes),
                metadata_={
                    "variant_index": vi,
                    "duration_sec": video.duration_sec,
                    "fps": video.fps,
                    "width": video.width,
                    "height": video.height,
                    "mode": effective_mode,
                    "seed": video.seed,
                    "prompt_preview": compiled.concise_prompt[:100],
                    "provider": response.provider,
                    "model": response.model,
                    "start_frame_asset_id": str(start_asset.id) if start_asset else None,
                    "end_frame_asset_id": str(end_asset.id) if end_asset else None,
                    "batch_id": batch_id,
                },
                version=variant_ver,
                generation_batch=batch_id,
                provider_run_id=provider_run.id,
                status="ready",
            )
            session.add(asset)
            await session.flush()
            await session.refresh(asset)
            asset_ids.append(str(asset.id))

            current_progress = 20 + progress_per_variant * (vi + 1)
            await _update_job_progress(job_id, min(current_progress, 85))

        # Auto-select first variant if no selection exists
        has_selection = (
            await session.execute(
                select(func.count())
                .where(
                    Asset.parent_type == "shot",
                    Asset.parent_id == sid,
                    Asset.asset_type == "video",
                    Asset.is_selected.is_(True),
                )
            )
        ).scalar()
        if not has_selection and asset_ids:
            first = (
                await session.execute(
                    select(Asset).where(Asset.id == uuid.UUID(asset_ids[0]))
                )
            ).scalar_one()
            first.is_selected = True

        # Update shot status
        shot_obj = (
            await session.execute(select(Shot).where(Shot.id == sid))
        ).scalar_one_or_none()
        if shot_obj:
            shot_obj.status = "video_ready"

        await session.commit()

    await _update_job_progress(job_id, 100)

    logger.info(
        "video_generate completed: shot=%s batch=%s assets=%d",
        shot_id, batch_id, len(asset_ids),
    )

    return {
        "shot_id": shot_id,
        "asset_ids": asset_ids,
        "num_variants": len(asset_ids),
        "generation_batch": batch_id,
        "mode": effective_mode,
        "duration_sec": duration,
        "provider": response.provider if asset_ids else "none",
        "model": response.model if asset_ids else "none",
    }
