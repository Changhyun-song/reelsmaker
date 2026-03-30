from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.project import Project
from shared.models.style_preset import StylePreset
from shared.schemas.style_preset import (
    StylePresetCreate,
    StylePresetListResponse,
    StylePresetResponse,
    StylePresetUpdate,
)

router = APIRouter()


@router.get(
    "/{project_id}/styles",
    response_model=StylePresetListResponse,
)
async def list_style_presets(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return project-specific + global presets."""
    result = await db.execute(
        select(StylePreset)
        .where(
            or_(
                StylePreset.project_id == project_id,
                StylePreset.is_global.is_(True),
            )
        )
        .order_by(StylePreset.is_global.desc(), StylePreset.name)
    )
    presets = list(result.scalars().all())
    return StylePresetListResponse(presets=presets, total=len(presets))


@router.post(
    "/{project_id}/styles",
    response_model=StylePresetResponse,
    status_code=201,
)
async def create_style_preset(
    project_id: UUID,
    data: StylePresetCreate,
    db: AsyncSession = Depends(get_db),
):
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    preset = StylePreset(
        project_id=project_id,
        **data.model_dump(),
    )
    db.add(preset)
    await db.flush()
    await db.refresh(preset)
    return preset


@router.get(
    "/{project_id}/styles/{preset_id}",
    response_model=StylePresetResponse,
)
async def get_style_preset(
    project_id: UUID,
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    preset = (await db.execute(select(StylePreset).where(StylePreset.id == preset_id))).scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="StylePreset not found")
    return preset


@router.patch(
    "/{project_id}/styles/{preset_id}",
    response_model=StylePresetResponse,
)
async def update_style_preset(
    project_id: UUID,
    preset_id: UUID,
    data: StylePresetUpdate,
    db: AsyncSession = Depends(get_db),
):
    preset = (await db.execute(select(StylePreset).where(StylePreset.id == preset_id))).scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="StylePreset not found")
    if preset.is_global:
        raise HTTPException(status_code=403, detail="Cannot modify global preset; duplicate it first")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(preset, field, value)
    await db.flush()
    await db.refresh(preset)
    return preset


@router.delete("/{project_id}/styles/{preset_id}", status_code=204)
async def delete_style_preset(
    project_id: UUID,
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    preset = (await db.execute(select(StylePreset).where(StylePreset.id == preset_id))).scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="StylePreset not found")
    if preset.is_global:
        raise HTTPException(status_code=403, detail="Cannot delete global preset")
    await db.delete(preset)


@router.post(
    "/{project_id}/styles/{preset_id}/duplicate",
    response_model=StylePresetResponse,
    status_code=201,
)
async def duplicate_style_preset(
    project_id: UUID,
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a preset (including global ones) into the project."""
    source = (await db.execute(select(StylePreset).where(StylePreset.id == preset_id))).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="StylePreset not found")

    clone = StylePreset(
        project_id=project_id,
        name=f"{source.name} (copy)",
        description=source.description,
        style_keywords=source.style_keywords,
        color_palette=source.color_palette,
        rendering_style=source.rendering_style,
        camera_language=source.camera_language,
        lighting_rules=source.lighting_rules,
        negative_rules=source.negative_rules,
        prompt_prefix=source.prompt_prefix,
        prompt_suffix=source.prompt_suffix,
        negative_prompt=source.negative_prompt,
        model_preferences=source.model_preferences,
        style_anchor=source.style_anchor,
        color_temperature=source.color_temperature,
        texture_quality=source.texture_quality,
        depth_style=source.depth_style,
        environment_rules=source.environment_rules,
        reference_asset_ids=source.reference_asset_ids,
        is_global=False,
    )
    db.add(clone)
    await db.flush()
    await db.refresh(clone)
    return clone


@router.post(
    "/{project_id}/active-style/{preset_id}",
    response_model=dict,
)
async def set_active_style(
    project_id: UUID,
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Set the project's active style preset."""
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    preset = (await db.execute(select(StylePreset).where(StylePreset.id == preset_id))).scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="StylePreset not found")

    proj.active_style_preset_id = preset_id
    await db.flush()
    return {"active_style_preset_id": str(preset_id)}
