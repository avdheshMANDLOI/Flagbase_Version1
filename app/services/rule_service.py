"""
Rule service — create and delete targeting rules for a flag.

v1 design decision: no update endpoint for rules.
If a user wants to change a rule, they delete and recreate it.
This keeps v1 simple — rule updates are rare and a delete+create
costs nothing at this scale.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.flag_repo import FlagRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.rule_repo import RuleRepository
from app.schemas.rule import RuleCreate, RuleResponse


class RuleService:
    def __init__(self, db: AsyncSession):
        self.rule_repo = RuleRepository(db)
        self.flag_repo = FlagRepository(db)
        self.project_repo = ProjectRepository(db)

    async def create(
        self, flag_id: uuid.UUID, data: RuleCreate, owner_id: uuid.UUID
    ) -> RuleResponse:
        flag = await self._get_owned_flag(flag_id, owner_id)

        rule = await self.rule_repo.create(
            flag_id=flag.id,
            rule_type=data.rule_type,
            operator=data.operator,
            value=data.value,
            effect=data.effect,
            priority=data.priority,
            attribute_key=data.attribute_key,
        )
        return RuleResponse.model_validate(rule)

    async def list(self, flag_id: uuid.UUID, owner_id: uuid.UUID) -> list[RuleResponse]:
        await self._get_owned_flag(flag_id, owner_id)
        rules = await self.rule_repo.list_by_flag(flag_id)
        return [RuleResponse.model_validate(r) for r in rules]

    async def delete(
        self, flag_id: uuid.UUID, rule_id: uuid.UUID, owner_id: uuid.UUID
    ) -> None:
        await self._get_owned_flag(flag_id, owner_id)

        rule = await self.rule_repo.get_by_id(rule_id)
        if not rule or rule.flag_id != flag_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found",
            )
        await self.rule_repo.delete(rule)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_owned_flag(self, flag_id: uuid.UUID, owner_id: uuid.UUID):
        """Fetch flag and verify caller owns the parent project."""
        flag = await self.flag_repo.get_by_id(flag_id)
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag not found",
            )
        project = await self.project_repo.get_by_id(flag.project_id)
        if not project or not project.is_active or project.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag not found",
            )
        return flag
