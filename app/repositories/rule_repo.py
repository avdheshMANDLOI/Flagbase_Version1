"""
Rule repository — all SQLAlchemy queries for flag targeting rules.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flag_rule import FlagRule


class RuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, rule_id: uuid.UUID) -> FlagRule | None:
        result = await self.db.execute(
            select(FlagRule).where(FlagRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def list_by_flag(self, flag_id: uuid.UUID) -> list[FlagRule]:
        """Return rules sorted by priority (lowest = evaluated first)."""
        result = await self.db.execute(
            select(FlagRule)
            .where(FlagRule.flag_id == flag_id)
            .order_by(FlagRule.priority.asc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        flag_id: uuid.UUID,
        rule_type: str,
        operator: str,
        value: str | list,
        effect: str,
        priority: int,
        attribute_key: str | None = None,
    ) -> FlagRule:
        rule = FlagRule(
            flag_id=flag_id,
            rule_type=rule_type,
            attribute_key=attribute_key,
            operator=operator,
            value=value,
            effect=effect,
            priority=priority,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete(self, rule: FlagRule) -> None:
        await self.db.delete(rule)
        await self.db.commit()
