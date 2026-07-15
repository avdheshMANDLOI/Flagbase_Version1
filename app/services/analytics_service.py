"""
Analytics service — resolves flag keys and delegates to EventRepository.

Why a service layer here?
  The route handler shouldn't know how to resolve flag_key → flag_id.
  That's business logic. The service handles it and keeps the route thin.
"""
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.flag import Flag
from app.repositories.event_repo import EventRepository
from app.schemas.analytics import (
    FlagAnalyticsResponse,
    FlagSummaryResponse,
    AnalyticsBucket,
    FlagSummaryVariation,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EventRepository(db)

    async def _resolve_flag(self, project_id: uuid.UUID, flag_key: str) -> Flag | None:
        result = await self.db.execute(
            select(Flag).where(
                Flag.project_id == project_id,
                Flag.name == flag_key,
            )
        )
        return result.scalar_one_or_none()

    async def get_timeseries(
        self,
        project_id: uuid.UUID,
        flag_key: str,
        from_time: datetime,
        to_time: datetime,
        granularity: str,
    ) -> FlagAnalyticsResponse | None:
        """
        Returns time-series data for a flag. Returns None if flag not found.
        """
        flag = await self._resolve_flag(project_id, flag_key)
        if not flag:
            return None

        buckets_raw = await self.repo.get_flag_timeseries(
            flag_id=flag.id,
            from_time=from_time,
            to_time=to_time,
            granularity=granularity,
        )

        total = sum(b["count"] for b in buckets_raw)

        return FlagAnalyticsResponse(
            flag_key=flag_key,
            from_time=from_time,
            to_time=to_time,
            granularity=granularity,
            total_evaluations=total,
            buckets=[
                AnalyticsBucket(
                    timestamp=b["timestamp"],
                    variation=b["variation"],
                    count=b["count"],
                )
                for b in buckets_raw
            ],
        )

    async def get_summary(
        self,
        project_id: uuid.UUID,
        flag_key: str,
        from_time: datetime,
        to_time: datetime,
    ) -> FlagSummaryResponse | None:
        """
        Returns total + per-variation breakdown. Returns None if flag not found.
        """
        flag = await self._resolve_flag(project_id, flag_key)
        if not flag:
            return None

        summary = await self.repo.get_flag_summary(
            flag_id=flag.id,
            from_time=from_time,
            to_time=to_time,
        )

        total = summary["total"]
        variations = [
            FlagSummaryVariation(
                variation=v,
                count=c,
                percentage=round((c / total * 100), 2) if total > 0 else 0.0,
            )
            for v, c in summary["variations"].items()
        ]

        return FlagSummaryResponse(
            flag_key=flag_key,
            from_time=from_time,
            to_time=to_time,
            total_evaluations=total,
            variations=variations,
        )