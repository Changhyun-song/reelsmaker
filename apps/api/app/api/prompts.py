"""Prompt preview API — compile prompts without persisting anything."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.frame_spec import FrameSpec
from shared.prompt_compiler import CompiledPrompt, compile_full
from shared.prompt_compiler.context_builder import build_compiler_context

router = APIRouter()


@router.get(
    "/{project_id}/frames/{frame_id}/prompt-preview",
    response_model=CompiledPrompt,
)
async def preview_frame_prompt(
    project_id: UUID,
    frame_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Compile and return a prompt preview for a specific frame spec."""
    try:
        ctx = await build_compiler_context(project_id, frame_id, db)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return compile_full(ctx)


@router.get(
    "/{project_id}/shots/{shot_id}/prompt-preview",
    response_model=list[CompiledPrompt],
)
async def preview_shot_prompts(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Compile and return prompt previews for all frame specs in a shot."""
    frames = list(
        (
            await db.execute(
                select(FrameSpec)
                .where(FrameSpec.shot_id == shot_id)
                .order_by(FrameSpec.order_index)
            )
        ).scalars().all()
    )
    if not frames:
        raise HTTPException(404, "No frames found for this shot")

    results: list[CompiledPrompt] = []
    for frame in frames:
        try:
            ctx = await build_compiler_context(project_id, frame.id, db)
        except ValueError as e:
            raise HTTPException(404, str(e))
        results.append(compile_full(ctx))
    return results
