"""
Event repository — write-only for evaluation and conversion events.

These tables are only written to in v1.
They are read from in v3 (analytics) and v4 (A/B test results).
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversion_event import ConversionEvent
from app.models.evaluation_event import EvaluationEvent


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_evaluation(
        self,
        flag_id: uuid.UUID,
        user_id_hash: str,
        result: bool,
        reason: str,
        variant: str | None = None,
        ab_test_id: uuid.UUID | None = None,
    ) -> None:
        """
        Write an evaluation event.
        Called from a BackgroundTask — never blocks the HTTP response.
        """
        event = EvaluationEvent(
            flag_id=flag_id,
            user_id_hash=user_id_hash,
            result=result,
            reason=reason,
            variant=variant,
            ab_test_id=ab_test_id,
        )
        self.db.add(event)
        await self.db.commit()

    async def record_conversion(
        self,
        flag_id: uuid.UUID,
        user_id_hash: str,
        event_name: str,
        variant: str | None = None,
        ab_test_id: uuid.UUID | None = None,
    ) -> None:
        """
        Write a conversion event (SDK track() call).
        Called from a BackgroundTask.
        """
        event = ConversionEvent(
            flag_id=flag_id,
            user_id_hash=user_id_hash,
            event_name=event_name,
            variant=variant,
            ab_test_id=ab_test_id,
        )
        self.db.add(event)
        await self.db.commit()
