from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.character_profile import CharacterProfile
from shared.models.project import Project
from shared.schemas.character_profile import (
    CharacterProfileCreate,
    CharacterProfileListResponse,
    CharacterProfileResponse,
    CharacterProfileUpdate,
)

router = APIRouter()


@router.get(
    "/{project_id}/characters",
    response_model=CharacterProfileListResponse,
)
async def list_characters(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CharacterProfile)
        .where(CharacterProfile.project_id == project_id)
        .order_by(CharacterProfile.name)
    )
    chars = list(result.scalars().all())
    return CharacterProfileListResponse(characters=chars, total=len(chars))


@router.post(
    "/{project_id}/characters",
    response_model=CharacterProfileResponse,
    status_code=201,
)
async def create_character(
    project_id: UUID,
    data: CharacterProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    proj = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    char = CharacterProfile(
        project_id=project_id,
        **data.model_dump(),
    )
    db.add(char)
    await db.flush()
    await db.refresh(char)
    return char


@router.get(
    "/{project_id}/characters/{char_id}",
    response_model=CharacterProfileResponse,
)
async def get_character(
    project_id: UUID,
    char_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    char = (
        await db.execute(
            select(CharacterProfile).where(
                CharacterProfile.id == char_id,
                CharacterProfile.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not char:
        raise HTTPException(status_code=404, detail="CharacterProfile not found")
    return char


@router.patch(
    "/{project_id}/characters/{char_id}",
    response_model=CharacterProfileResponse,
)
async def update_character(
    project_id: UUID,
    char_id: UUID,
    data: CharacterProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    char = (
        await db.execute(
            select(CharacterProfile).where(
                CharacterProfile.id == char_id,
                CharacterProfile.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not char:
        raise HTTPException(status_code=404, detail="CharacterProfile not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(char, field, value)
    await db.flush()
    await db.refresh(char)
    return char


@router.delete("/{project_id}/characters/{char_id}", status_code=204)
async def delete_character(
    project_id: UUID,
    char_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    char = (
        await db.execute(
            select(CharacterProfile).where(
                CharacterProfile.id == char_id,
                CharacterProfile.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if not char:
        raise HTTPException(status_code=404, detail="CharacterProfile not found")
    await db.delete(char)
