"""
Flag routes — CRUD for feature flags within a project.

Auth: JWT Bearer (dashboard users only)
Prefix: /api/v1/projects/{project_id}/flags
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.flag import FlagCreate, FlagListResponse, FlagResponse, FlagUpdate
from app.services.flag_service import FlagService

router = APIRouter()


@router.post("", response_model=FlagResponse, status_code=status.HTTP_201_CREATED)
async def create_flag(
    project_id: uuid.UUID,
    data: FlagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new feature flag in a project."""
    return await FlagService(db).create(project_id, data, current_user.id)


@router.get("", response_model=FlagListResponse)
async def list_flags(
    project_id: uuid.UUID,
    status: str | None = Query(None, pattern="^(enabled|disabled)$"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List flags in a project with optional filters."""
    return await FlagService(db).list(
        project_id, current_user.id, status=status, search=search, page=page, limit=limit
    )


@router.get("/{flag_id}", response_model=FlagResponse)
async def get_flag(
    project_id: uuid.UUID,
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single flag by ID."""
    return await FlagService(db).get(flag_id, current_user.id)


@router.patch("/{flag_id}", response_model=FlagResponse)
async def update_flag(
    project_id: uuid.UUID,
    flag_id: uuid.UUID,
    data: FlagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a flag's name, description, enabled state, or rollout percentage."""
    return await FlagService(db).update(flag_id, data, current_user.id)


@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    project_id: uuid.UUID,
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a flag (sets is_archived=True)."""
    await FlagService(db).delete(flag_id, current_user.id)
