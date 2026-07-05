"""
Flag service — business logic for flag CRUD.

Responsibilities:
  - Ownership checks (does this user own the project?)
  - Uniqueness checks (is this flag name already taken in the project?)
  - Delegating DB access to FlagRepository

Never:
  - Direct SQLAlchemy queries (belongs in repository)
  - HTTP request/response handling (belongs in router)
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.flag_repo import FlagRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.flag import FlagCreate, FlagListResponse, FlagResponse, FlagUpdate


class FlagService:
    def __init__(self, db: AsyncSession):
        self.flag_repo = FlagRepository(db)
        self.project_repo = ProjectRepository(db)

    async def create(
        self, project_id: uuid.UUID, data: FlagCreate, owner_id: uuid.UUID
    ) -> FlagResponse:
        await self._assert_project_ownership(project_id, owner_id)

        # Ensure flag name is unique within the project
        existing = await self.flag_repo.get_by_name(project_id, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A flag named '{data.name}' already exists in this project",
            )

        flag = await self.flag_repo.create(
            project_id=project_id,
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            rollout_percentage=data.rollout_percentage,
        )
        return FlagResponse.model_validate(flag)

    async def list(
        self,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> FlagListResponse:
        await self._assert_project_ownership(project_id, owner_id)
        flags, total = await self.flag_repo.list_by_project(
            project_id, status=status, search=search, page=page, limit=limit
        )
        return FlagListResponse(
            flags=[FlagResponse.model_validate(f) for f in flags],
            total=total,
            page=page,
        )

    async def get(self, flag_id: uuid.UUID, owner_id: uuid.UUID) -> FlagResponse:
        flag = await self._get_owned_flag(flag_id, owner_id)
        return FlagResponse.model_validate(flag)

    async def update(
        self, flag_id: uuid.UUID, data: FlagUpdate, owner_id: uuid.UUID
    ) -> FlagResponse:
        flag = await self._get_owned_flag(flag_id, owner_id)
        updates = data.model_dump(exclude_unset=True)
        if updates:
            flag = await self.flag_repo.update(flag, **updates)
        return FlagResponse.model_validate(flag)

    async def delete(self, flag_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        flag = await self._get_owned_flag(flag_id, owner_id)
        await self.flag_repo.archive(flag)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _assert_project_ownership(
        self, project_id: uuid.UUID, owner_id: uuid.UUID
    ) -> None:
        """Raise 404 if the project doesn't exist or isn't owned by this user."""
        project = await self.project_repo.get_by_id(project_id)
        if not project or not project.is_active or project.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

    async def _get_owned_flag(self, flag_id: uuid.UUID, owner_id: uuid.UUID):
        """Fetch a flag and verify the caller owns the parent project."""
        flag = await self.flag_repo.get_by_id(flag_id)
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag not found",
            )
        # Verify project ownership
        await self._assert_project_ownership(flag.project_id, owner_id)
        return flag
