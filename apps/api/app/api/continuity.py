"""Continuity profile API — manage project-level visual consistency rules."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database import get_db
from shared.models.character_profile import CharacterProfile
from shared.models.continuity_profile import ContinuityProfile
from shared.models.project import Project
from shared.prompt_compiler.context_builder import build_continuity_text_block
from shared.schemas.continuity import (
    ContinuityContextResponse,
    ContinuityProfileResponse,
    ContinuityProfileUpdate,
)

router = APIRouter()


async def _get_or_create(project_id: UUID, db: AsyncSession) -> ContinuityProfile:
    cp = (
        await db.execute(
            select(ContinuityProfile).where(ContinuityProfile.project_id == project_id)
        )
    ).scalar_one_or_none()
    if cp is None:
        proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not proj:
            raise HTTPException(404, "Project not found")
        cp = ContinuityProfile(project_id=project_id)
        db.add(cp)
        await db.flush()
        await db.refresh(cp)
    return cp


@router.get(
    "/{project_id}/continuity",
    response_model=ContinuityProfileResponse,
)
async def get_continuity_profile(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    cp = await _get_or_create(project_id, db)
    return cp


@router.put(
    "/{project_id}/continuity",
    response_model=ContinuityProfileResponse,
)
async def update_continuity_profile(
    project_id: UUID,
    data: ContinuityProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    cp = await _get_or_create(project_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cp, field, value)
    await db.flush()
    await db.refresh(cp)
    return cp


@router.get(
    "/{project_id}/continuity/preview",
    response_model=ContinuityContextResponse,
)
async def preview_continuity_context(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Compile and return the continuity context that would be injected into prompts."""
    project = (
        await db.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.active_style_preset))
        )
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    characters = list(
        (await db.execute(
            select(CharacterProfile).where(CharacterProfile.project_id == project_id)
        )).scalars().all()
    )
    cp = (
        await db.execute(
            select(ContinuityProfile).where(ContinuityProfile.project_id == project_id)
        )
    ).scalar_one_or_none()

    style = project.active_style_preset

    # Build style anchor
    style_anchor = ""
    if style:
        style_anchor = style.style_anchor or style.rendering_style or style.name or ""

    # Build character anchors
    char_anchors: list[str] = []
    for c in characters:
        parts = [p for p in [c.appearance, c.body_type, c.outfit, c.hair_description] if p]
        if parts:
            char_anchors.append(f"[{c.name}] {'; '.join(parts)}")

    # Build color rules
    color_parts: list[str] = []
    if cp and cp.color_palette_lock:
        color_parts.append(cp.color_palette_lock)
    elif style and style.color_palette:
        color_parts.append(style.color_palette)
    if style and style.color_temperature:
        color_parts.append(style.color_temperature)
    elif cp and cp.color_temperature_range:
        color_parts.append(cp.color_temperature_range)

    # Build lighting rules
    lighting = ""
    if cp and cp.lighting_anchor:
        lighting = cp.lighting_anchor
    elif style and style.lighting_rules:
        lighting = style.lighting_rules

    # Build environment rules
    env = ""
    if cp and cp.environment_consistency:
        env = cp.environment_consistency
    elif style and style.environment_rules:
        env = style.environment_rules

    # Build forbidden drift
    drift_items: list[str] = []
    if cp and cp.forbidden_global_drift:
        drift_items.append(cp.forbidden_global_drift)
    for c in characters:
        if c.forbidden_drift:
            drift_items.append(f"[{c.name}] {c.forbidden_drift}")
        elif c.forbidden_changes:
            drift_items.append(f"[{c.name}] {c.forbidden_changes}")

    # Count reference assets
    ref_count = 0
    if cp and cp.reference_asset_ids:
        ref_count += len(cp.reference_asset_ids)
    if style and style.reference_asset_ids:
        ref_count += len(style.reference_asset_ids)
    for c in characters:
        if c.reference_asset_ids:
            ref_count += len(c.reference_asset_ids)
        if c.reference_asset_id:
            ref_count += 1

    return ContinuityContextResponse(
        style_anchor=style_anchor,
        character_anchors=char_anchors,
        color_rules=", ".join(color_parts),
        lighting_rules=lighting,
        environment_rules=env,
        forbidden_drift=drift_items,
        reference_count=ref_count,
    )
