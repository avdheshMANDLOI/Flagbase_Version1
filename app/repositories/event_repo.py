"""
Event repository — write-only for evaluation and conversion events.

These tables are only written to in v1.
They are read from in v3 (analytics) and v4 (A/B test results).
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
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
    
    async def ingest_batch(
        self,
        project_id: uuid.UUID,
        events: list[dict],
    ) -> int:
        """
        Upsert a batch of raw events into the hourly aggregation table.

        Why UPSERT instead of INSERT + SELECT?
          Concurrent requests could both try to INSERT the same (flag_id, hour, variation)
          row. UPSERT handles this atomically — increment if exists, insert if not.

        Returns the number of events successfully processed.
        """
        from datetime import timezone
        from sqlalchemy import select, update
        from app.models.flag import Flag
        from app.models.event_aggregation import EventAggregation

        processed = 0

        for event in events:
            # Resolve flag_key → flag_id (scoped to project)
            result = await self.db.execute(
                select(Flag).where(
                    Flag.project_id == project_id,
                    Flag.name == event["flag_key"],
                )
            )
            flag = result.scalar_one_or_none()
            if not flag:
                continue  # silently drop unknown flags — never error the SDK

            # Truncate timestamp to the hour
            ts: datetime = event.get("timestamp") or datetime.now(timezone.utc)
            hour = ts.replace(minute=0, second=0, microsecond=0)

            # Try to find existing aggregation row
            agg_result = await self.db.execute(
                select(EventAggregation).where(
                    EventAggregation.flag_id == flag.id,
                    EventAggregation.hour == hour,
                    EventAggregation.variation == event["variation"],
                )
            )
            agg = agg_result.scalar_one_or_none()

            if agg:
                agg.count += 1
            else:
                agg = EventAggregation(
                    flag_id=flag.id,
                    hour=hour,
                    variation=event["variation"],
                    count=1,
                )
                self.db.add(agg)

            processed += 1

        await self.db.commit()
        return processed