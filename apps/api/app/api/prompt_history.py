"""Prompt version history API — list, compare, restore, clone."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from shared.database import get_db
from shared.models.asset import Asset
from shared.models.frame_spec import FrameSpec
from shared.models.prompt_history import PromptHistory
from shared.storage import get_presigned_url

router = APIRouter()


# ── Schemas ──────────────────────────────────────────


class PromptHistoryItem(BaseModel):
    id: str
    version: int
    prompt_text: str
    negative_prompt: str | None
    prompt_source: str
    quality_mode: str | None
    generation_batch: str | None
    asset_id: str | None
    provider: str | None
    model: str | None
    is_current: bool
    created_at: str
    thumbnail_url: str | None = None
    asset_status: str | None = None
    metadata_: dict | None = None


class CompareResult(BaseModel):
    version_a: PromptHistoryItem
    version_b: PromptHistoryItem
    diff: list[dict]


class RestoreRequest(BaseModel):
    version_id: str


# ── Helpers ──────────────────────────────────────────


def _to_item(h: PromptHistory, thumb_url: str | None = None, asset_status: str | None = None) -> PromptHistoryItem:
    return PromptHistoryItem(
        id=str(h.id),
        version=h.version,
        prompt_text=h.prompt_text or "",
        negative_prompt=h.negative_prompt,
        prompt_source=h.prompt_source or "compiler",
        quality_mode=h.quality_mode,
        generation_batch=h.generation_batch,
        asset_id=str(h.asset_id) if h.asset_id else None,
        provider=h.provider,
        model=h.model,
        is_current=h.is_current,
        created_at=h.created_at.isoformat() if h.created_at else "",
        thumbnail_url=thumb_url,
        asset_status=asset_status,
        metadata_=h.metadata_,
    )


def _compute_diff(text_a: str, text_b: str) -> list[dict]:
    """Sentence-level diff between two prompts."""
    import re
    split_re = re.compile(r'(?<=[.!?,;])\s+')
    sents_a = [s.strip() for s in split_re.split(text_a) if s.strip()]
    sents_b = [s.strip() for s in split_re.split(text_b) if s.strip()]

    set_a = set(sents_a)
    set_b = set(sents_b)

    result: list[dict] = []
    for s in sents_a:
        if s in set_b:
            result.append({"type": "unchanged", "text": s})
        else:
            result.append({"type": "removed", "text": s})
    for s in sents_b:
        if s not in set_a:
            result.append({"type": "added", "text": s})
    return result


async def _get_thumbnail(asset_id: UUID | None, db: AsyncSession) -> tuple[str | None, str | None]:
    """Get presigned thumbnail URL and asset status."""
    if not asset_id:
        return None, None
    asset = (await db.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
    if not asset or not asset.storage_key:
        return None, asset.status if asset else None
    try:
        url = get_presigned_url(asset.storage_key)
        return url, asset.status
    except Exception:
        return None, asset.status if asset else None


# ── Endpoints ────────────────────────────────────────


@router.get("/{project_id}/frames/{frame_id}/prompt-history")
async def list_prompt_history(
    project_id: str,
    frame_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """List all prompt versions for a given frame, newest first."""
    rows = (
        await db.execute(
            select(PromptHistory)
            .where(
                PromptHistory.project_id == UUID(project_id),
                PromptHistory.frame_id == UUID(frame_id),
            )
            .order_by(desc(PromptHistory.version))
        )
    ).scalars().all()

    items: list[dict] = []
    for h in rows:
        thumb, status = await _get_thumbnail(h.asset_id, db)
        items.append(_to_item(h, thumb, status).model_dump())

    return {"frame_id": frame_id, "versions": items, "total": len(items)}


@router.get("/{project_id}/frames/{frame_id}/prompt-history/compare")
async def compare_prompts(
    project_id: str,
    frame_id: str,
    version_a: str,
    version_b: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Compare two prompt versions by their IDs."""
    ha = (
        await db.execute(
            select(PromptHistory).where(PromptHistory.id == UUID(version_a))
        )
    ).scalar_one_or_none()
    hb = (
        await db.execute(
            select(PromptHistory).where(PromptHistory.id == UUID(version_b))
        )
    ).scalar_one_or_none()

    if not ha or not hb:
        raise HTTPException(404, "One or both versions not found")

    thumb_a, status_a = await _get_thumbnail(ha.asset_id, db)
    thumb_b, status_b = await _get_thumbnail(hb.asset_id, db)

    diff = _compute_diff(ha.prompt_text or "", hb.prompt_text or "")

    return CompareResult(
        version_a=_to_item(ha, thumb_a, status_a),
        version_b=_to_item(hb, thumb_b, status_b),
        diff=diff,
    ).model_dump()


@router.post("/{project_id}/frames/{frame_id}/prompt-history/restore")
async def restore_prompt(
    project_id: str,
    frame_id: str,
    body: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Restore a past prompt version as the current prompt on the frame."""
    source = (
        await db.execute(
            select(PromptHistory).where(PromptHistory.id == UUID(body.version_id))
        )
    ).scalar_one_or_none()
    if not source:
        raise HTTPException(404, "Source version not found")

    fid = UUID(frame_id)

    # Update frame spec
    frame = (
        await db.execute(select(FrameSpec).where(FrameSpec.id == fid))
    ).scalar_one_or_none()
    if not frame:
        raise HTTPException(404, "Frame not found")

    frame.visual_prompt = source.prompt_text
    frame.negative_prompt = source.negative_prompt

    # Mark all existing as not current, then create a new "restored" entry
    await db.execute(
        update(PromptHistory)
        .where(PromptHistory.frame_id == fid)
        .values(is_current=False)
    )

    max_ver = (
        await db.execute(
            select(func.coalesce(func.max(PromptHistory.version), 0))
            .where(PromptHistory.frame_id == fid)
        )
    ).scalar() or 0

    new_entry = PromptHistory(
        project_id=UUID(project_id),
        frame_id=fid,
        version=max_ver + 1,
        prompt_text=source.prompt_text,
        negative_prompt=source.negative_prompt,
        prompt_source="restored",
        quality_mode=source.quality_mode,
        is_current=True,
        metadata_={"restored_from_version": source.version, "restored_from_id": str(source.id)},
    )
    db.add(new_entry)
    await db.commit()

    return {
        "restored": True,
        "new_version": max_ver + 1,
        "restored_from": source.version,
        "frame_id": frame_id,
    }


@router.post("/{project_id}/frames/{frame_id}/prompt-history/clone")
async def clone_prompt(
    project_id: str,
    frame_id: str,
    body: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Clone a past prompt as a new editable version (doesn't overwrite current frame)."""
    source = (
        await db.execute(
            select(PromptHistory).where(PromptHistory.id == UUID(body.version_id))
        )
    ).scalar_one_or_none()
    if not source:
        raise HTTPException(404, "Source version not found")

    fid = UUID(frame_id)
    max_ver = (
        await db.execute(
            select(func.coalesce(func.max(PromptHistory.version), 0))
            .where(PromptHistory.frame_id == fid)
        )
    ).scalar() or 0

    new_entry = PromptHistory(
        project_id=UUID(project_id),
        frame_id=fid,
        version=max_ver + 1,
        prompt_text=source.prompt_text,
        negative_prompt=source.negative_prompt,
        prompt_source="manual",
        quality_mode=source.quality_mode,
        is_current=False,
        metadata_={"cloned_from_version": source.version, "cloned_from_id": str(source.id)},
    )
    db.add(new_entry)
    await db.commit()

    return {
        "cloned": True,
        "new_version": max_ver + 1,
        "cloned_from": source.version,
        "id": str(new_entry.id),
    }
