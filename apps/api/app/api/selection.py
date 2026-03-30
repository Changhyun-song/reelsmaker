"""Asset / VoiceTrack variant selection API.

Selecting a variant auto-deselects siblings in the same
(parent_type, parent_id, asset_type) group or (shot_id) group.
Also provides quality_note update and shot variant summary.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.frame_spec import FrameSpec
from shared.models.shot import Shot
from shared.models.voice_track import VoiceTrack

router = APIRouter()


class SelectionResponse(BaseModel):
    id: str
    is_selected: bool


class QualityNoteRequest(BaseModel):
    quality_note: str | None = Field(None, max_length=500)


class QualityNoteResponse(BaseModel):
    id: str
    quality_note: str | None


class VariantGroupSummary(BaseModel):
    parent_type: str
    parent_id: str
    asset_type: str
    total: int
    ready: int
    selected_id: str | None
    latest_batch: str | None


class ShotVariantSummary(BaseModel):
    shot_id: str
    image_groups: list[VariantGroupSummary]
    video_group: VariantGroupSummary | None
    has_all_selections: bool


@router.patch(
    "/{project_id}/assets/{asset_id}/select",
    response_model=SelectionResponse,
)
async def select_asset(
    project_id: UUID,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark an asset as the selected variant, deselecting siblings."""
    asset = (
        await db.execute(select(Asset).where(Asset.id == asset_id))
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset.project_id != project_id:
        raise HTTPException(404, "Asset not found in this project")
    if asset.status != "ready":
        raise HTTPException(400, "Only ready assets can be selected")

    await db.execute(
        update(Asset)
        .where(
            Asset.parent_type == asset.parent_type,
            Asset.parent_id == asset.parent_id,
            Asset.asset_type == asset.asset_type,
            Asset.is_selected == True,  # noqa: E712
        )
        .values(is_selected=False)
    )

    asset.is_selected = True
    await db.flush()
    await db.refresh(asset)

    return SelectionResponse(id=str(asset.id), is_selected=True)


@router.patch(
    "/{project_id}/assets/{asset_id}/deselect",
    response_model=SelectionResponse,
)
async def deselect_asset(
    project_id: UUID,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Deselect an asset variant (falls back to 'latest' for timeline)."""
    asset = (
        await db.execute(select(Asset).where(Asset.id == asset_id))
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    asset.is_selected = False
    await db.flush()
    await db.refresh(asset)

    return SelectionResponse(id=str(asset.id), is_selected=False)


@router.patch(
    "/{project_id}/voice-tracks/{track_id}/select",
    response_model=SelectionResponse,
)
async def select_voice_track(
    project_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a voice track as the selected variant for its shot."""
    track = (
        await db.execute(select(VoiceTrack).where(VoiceTrack.id == track_id))
    ).scalar_one_or_none()
    if not track:
        raise HTTPException(404, "VoiceTrack not found")
    if track.project_id != project_id:
        raise HTTPException(404, "VoiceTrack not found in this project")
    if track.status != "ready":
        raise HTTPException(400, "Only ready voice tracks can be selected")

    if track.shot_id:
        await db.execute(
            update(VoiceTrack)
            .where(
                VoiceTrack.shot_id == track.shot_id,
                VoiceTrack.is_selected == True,  # noqa: E712
            )
            .values(is_selected=False)
        )

    track.is_selected = True
    await db.flush()
    await db.refresh(track)

    return SelectionResponse(id=str(track.id), is_selected=True)


@router.patch(
    "/{project_id}/voice-tracks/{track_id}/deselect",
    response_model=SelectionResponse,
)
async def deselect_voice_track(
    project_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Deselect a voice track variant."""
    track = (
        await db.execute(select(VoiceTrack).where(VoiceTrack.id == track_id))
    ).scalar_one_or_none()
    if not track:
        raise HTTPException(404, "VoiceTrack not found")

    track.is_selected = False
    await db.flush()
    await db.refresh(track)

    return SelectionResponse(id=str(track.id), is_selected=False)


# ── Quality Note ──────────────────────────────────────


@router.patch(
    "/{project_id}/assets/{asset_id}/note",
    response_model=QualityNoteResponse,
)
async def update_quality_note(
    project_id: UUID,
    asset_id: UUID,
    body: QualityNoteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a quality memo on an asset variant."""
    asset = (
        await db.execute(select(Asset).where(Asset.id == asset_id))
    ).scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset.project_id != project_id:
        raise HTTPException(404, "Asset not found in this project")

    asset.quality_note = body.quality_note
    await db.flush()
    await db.refresh(asset)

    return QualityNoteResponse(id=str(asset.id), quality_note=asset.quality_note)


# ── Shot variant summary ─────────────────────────────


@router.get(
    "/{project_id}/shots/{shot_id}/variants",
    response_model=ShotVariantSummary,
)
async def shot_variant_summary(
    project_id: UUID,
    shot_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a summary of all asset variants for a shot (images + video)."""
    shot = (
        await db.execute(select(Shot).where(Shot.id == shot_id))
    ).scalar_one_or_none()
    if not shot:
        raise HTTPException(404, "Shot not found")

    # Gather frame specs for this shot
    frames = (
        await db.execute(
            select(FrameSpec)
            .where(FrameSpec.shot_id == shot_id)
            .order_by(FrameSpec.order_index)
        )
    ).scalars().all()

    image_groups: list[VariantGroupSummary] = []
    for fr in frames:
        assets = (
            await db.execute(
                select(Asset)
                .where(
                    Asset.parent_type == "frame_spec",
                    Asset.parent_id == fr.id,
                    Asset.asset_type == "image",
                )
                .order_by(Asset.created_at.desc())
            )
        ).scalars().all()

        ready = [a for a in assets if a.status == "ready"]
        selected = next((a for a in ready if a.is_selected), None)
        latest_batch = assets[0].generation_batch if assets else None

        image_groups.append(VariantGroupSummary(
            parent_type="frame_spec",
            parent_id=str(fr.id),
            asset_type="image",
            total=len(assets),
            ready=len(ready),
            selected_id=str(selected.id) if selected else None,
            latest_batch=latest_batch,
        ))

    # Video variants
    vid_assets = (
        await db.execute(
            select(Asset)
            .where(
                Asset.parent_type == "shot",
                Asset.parent_id == shot_id,
                Asset.asset_type == "video",
            )
            .order_by(Asset.created_at.desc())
        )
    ).scalars().all()

    vid_ready = [a for a in vid_assets if a.status == "ready"]
    vid_selected = next((a for a in vid_ready if a.is_selected), None)
    vid_latest_batch = vid_assets[0].generation_batch if vid_assets else None

    video_group = VariantGroupSummary(
        parent_type="shot",
        parent_id=str(shot_id),
        asset_type="video",
        total=len(vid_assets),
        ready=len(vid_ready),
        selected_id=str(vid_selected.id) if vid_selected else None,
        latest_batch=vid_latest_batch,
    ) if vid_assets else None

    has_all = (
        all(g.selected_id is not None for g in image_groups if g.ready > 0)
        and (video_group is None or video_group.selected_id is not None)
    )

    return ShotVariantSummary(
        shot_id=str(shot_id),
        image_groups=image_groups,
        video_group=video_group,
        has_all_selections=has_all,
    )
