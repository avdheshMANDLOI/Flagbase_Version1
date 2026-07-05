"""
Flag repository — all SQLAlchemy queries for flags.

Rule: only DB access here. No business logic, no HTTP exceptions.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.flag import Flag


class FlagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, flag_id: uuid.UUID) -> Flag | None:
        """Fetch a flag by its ID, eagerly loading its rules."""
        result = await self.db.execute(
            select(Flag)
            .where(Flag.id == flag_id, Flag.is_archived == False)
            .options(selectinload(Flag.rules))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, project_id: uuid.UUID, name: str) -> Flag | None:
        """Fetch a flag by project + name (used by evaluation engine)."""
        result = await self.db.execute(
            select(Flag)
            .where(
                Flag.project_id == project_id,
                Flag.name == name,
                Flag.is_archived == False,
            )
            .options(selectinload(Flag.rules))
        )
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Flag], int]:
        """
        List flags for a project with optional filters.
        Returns (flags, total_count).
        """
        query = select(Flag).where(
            Flag.project_id == project_id,
            Flag.is_archived == False,
        )

        if status == "enabled":
            query = query.where(Flag.is_enabled == True)
        elif status == "disabled":
            query = query.where(Flag.is_enabled == False)

        if search:
            query = query.where(Flag.name.ilike(f"%{search}%"))

        # Total count before pagination
        count_result = await self.db.execute(
            select(Flag.id).where(
                Flag.project_id == project_id,
                Flag.is_archived == False,
            )
        )
        total = len(count_result.all())

        # Paginated results
        query = query.order_by(Flag.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(
        self,
        project_id: uuid.UUID,
        name: str,
        display_name: str,
        description: str | None,
        rollout_percentage: int = 0,
) -> Flag:
        flag = Flag(
        project_id=project_id,
        name=name,
        display_name=display_name,
        description=description,
        rollout_percentage=rollout_percentage,
    )
        self.db.add(flag)
        await self.db.commit()
        await self.db.refresh(flag)
        return flag

    async def update(self, flag: Flag, **kwargs) -> Flag:
        for key, value in kwargs.items():
            setattr(flag, key, value)
        await self.db.commit()
        await self.db.refresh(flag)
        return flag

    async def archive(self, flag: Flag) -> None:
        """Soft delete — sets is_archived=True."""
        flag.is_archived = True
        await self.db.commit()
