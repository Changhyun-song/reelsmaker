from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from shared.models.project import Project
from shared.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.auth import get_current_user

router = APIRouter()


def _user_filter(user_id: str):
    """Match projects owned by user OR with no owner (legacy)."""
    return or_(Project.user_id == user_id, Project.user_id.is_(None))


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .where(_user_filter(user_id))
        .order_by(Project.updated_at.desc())
    )
    projects = result.scalars().all()
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    dump = data.model_dump()
    if dump.get("settings") is not None:
        dump["settings"] = data.settings.model_dump()
    dump["user_id"] = user_id
    project = Project(**dump)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, _user_filter(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, _user_filter(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    if "settings" in update_data and update_data["settings"] is not None:
        update_data["settings"] = data.settings.model_dump()
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, _user_filter(user_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
