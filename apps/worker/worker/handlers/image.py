"""Worker handler for image generation.

Flow: compile prompt → call ImageProvider → upload to S3 → create Asset + ProviderRun rows.
Non-destructive: never deletes existing assets. Each run gets a unique generation_batch.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select

from shared.database import async_session_factory
from shared.models.asset import Asset
from shared.models.frame_spec import FrameSpec
from shared.models.provider_run import ProviderRun
from shared.prompt_compiler import compile_full
from shared.prompt_compiler.context_builder import build_compiler_context
from shared.providers.factory import get_image_provider
from shared.providers.image_base import ImageGenerationRequest
from shared.storage import ensure_bucket, generate_storage_key, upload_bytes

logger = logging.getLogger("reelsmaker.worker.image")


async def _update_job_progress(job_id: str, progress: int) -> None:
    from worker.main import _update_job
    await _update_job(job_id, progress=progress)


async def _next_version(parent_id: uuid.UUID) -> int:
    """Get the next version number for assets of a given frame spec."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.coalesce(func.max(Asset.version), 0))
            .where(
                Asset.parent_type == "frame_spec",
                Asset.parent_id == parent_id,
            )
        )
        return (result.scalar() or 0) + 1


async def handle_image_generate(
    job_id: str,
    project_id: str,
    frame_id: str,
    num_variants: int = 2,
    **_params,
) -> dict:
    """Generate images for a single FrameSpec.

    Non-destructive: existing assets are preserved. New assets get incremented
    version numbers and a unique generation_batch ID for grouping.
    """
    pid = uuid.UUID(project_id)
    fid = uuid.UUID(frame_id)
    num_variants = max(1, min(num_variants, 4))
    batch_id = f"img-{uuid.uuid4().hex[:12]}"

    ensure_bucket()
    await _update_job_progress(job_id, 5)

    # 1. Compile prompt — use story-generated prompt if available, else compile from spec
    async with async_session_factory() as session:
        frame_check = (
            await session.execute(select(FrameSpec).where(FrameSpec.id == fid))
        ).scalar_one_or_none()
        has_story_prompt = bool(frame_check and frame_check.visual_prompt)
        ctx = await build_compiler_context(pid, fid, session)

    compiled = compile_full(ctx)
    if has_story_prompt and frame_check.visual_prompt:
        compiled.detailed_prompt = frame_check.visual_prompt
        compiled.concise_prompt = frame_check.visual_prompt[:200]
        if frame_check.negative_prompt:
            compiled.negative_prompt = frame_check.negative_prompt
        logger.info("Using story-generated prompt for frame=%s", frame_id)

    next_ver = await _next_version(fid)
    await _update_job_progress(job_id, 15)

    logger.info(
        "image_generate frame=%s batch=%s version=%d variants=%d",
        frame_id, batch_id, next_ver, num_variants,
    )

    # 2. Call image provider
    provider = get_image_provider()
    request = ImageGenerationRequest(
        prompt=compiled.detailed_prompt,
        negative_prompt=compiled.negative_prompt,
        width=ctx.project.width,
        height=ctx.project.height,
        num_variants=num_variants,
        provider_options=compiled.provider_options,
    )

    response = await provider.generate(request)
    await _update_job_progress(job_id, 50)

    # 3. Upload + create assets
    asset_ids: list[str] = []

    async with async_session_factory() as session:
        provider_run = ProviderRun(
            project_id=pid,
            provider=response.provider,
            operation="image_generate",
            model=response.model,
            input_params={
                "prompt": compiled.detailed_prompt[:500],
                "negative_prompt": compiled.negative_prompt[:200],
                "width": request.width,
                "height": request.height,
                "num_variants": num_variants,
                "batch_id": batch_id,
            },
            output_summary={
                "num_images": len(response.images),
                "latency_ms": response.latency_ms,
            },
            status="completed",
            latency_ms=response.latency_ms,
            cost_estimate=response.cost_estimate,
        )
        session.add(provider_run)
        await session.flush()
        await session.refresh(provider_run)

        progress_per_image = 40 // max(len(response.images), 1)

        for img in response.images:
            variant_ver = next_ver + img.variant_index
            storage_key = generate_storage_key(
                project_id=pid,
                parent_type="frame_spec",
                parent_id=fid,
                variant_index=variant_ver,
                extension="png",
            )

            upload_bytes(storage_key, img.image_bytes, content_type=img.mime_type)

            asset = Asset(
                project_id=pid,
                parent_type="frame_spec",
                parent_id=fid,
                asset_type="image",
                storage_key=storage_key,
                filename=storage_key.split("/")[-1],
                mime_type=img.mime_type,
                file_size_bytes=len(img.image_bytes),
                metadata_={
                    "variant_index": img.variant_index,
                    "width": img.width,
                    "height": img.height,
                    "seed": img.seed,
                    "prompt_preview": compiled.concise_prompt[:100],
                    "provider": response.provider,
                    "model": response.model,
                    "frame_role": ctx.frame.frame_role,
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

            current = 50 + progress_per_image * (img.variant_index + 1)
            await _update_job_progress(job_id, min(current, 90))

        # Auto-select first variant if no selection exists for this frame
        has_selection = (
            await session.execute(
                select(func.count())
                .where(
                    Asset.parent_type == "frame_spec",
                    Asset.parent_id == fid,
                    Asset.asset_type == "image",
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

        # Update FrameSpec status
        frame = (
            await session.execute(select(FrameSpec).where(FrameSpec.id == fid))
        ).scalar_one_or_none()
        if frame:
            frame.status = "generated"
            frame.visual_prompt = compiled.detailed_prompt
            frame.negative_prompt = compiled.negative_prompt

        await session.commit()

    await _update_job_progress(job_id, 100)

    logger.info(
        "image_generate completed: frame=%s batch=%s assets=%d",
        frame_id, batch_id, len(asset_ids),
    )

    return {
        "frame_id": frame_id,
        "asset_ids": asset_ids,
        "num_variants": len(response.images),
        "generation_batch": batch_id,
        "version_start": next_ver,
        "provider": response.provider,
        "model": response.model,
    }
