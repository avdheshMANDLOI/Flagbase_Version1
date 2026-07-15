"""
Analytics endpoints.

Ingestion:  POST /api/v1/analytics/events          (SDK API key auth)
Query:      GET  /api/v1/analytics/flags/{flag_key}          (JWT auth)
            GET  /api/v1/analytics/flags/{flag_key}/summary  (JWT auth)

Why different auth for ingestion vs query?
  Ingestion is called by the SDK running in user applications — API key.
  Querying analytics is done by developers in the dashboard — JWT.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_project_from_api_key
from app.core.event_queue import enqueue_events
from app.models.user import User
from app.repositories.project_repo import ProjectRepository
from app.schemas.analytics import (
    IngestEventsRequest,
    IngestEventsResponse,
    FlagAnalyticsResponse,
    FlagSummaryResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()


# ── Ingestion (SDK-facing, API key auth) ─────────────────────────────────────

@router.post(
    "/analytics/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestEventsResponse,
)
async def ingest_events(
    request: IngestEventsRequest,
    project_id: uuid.UUID = Depends(get_project_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a batch of evaluation events from the SDK.
    Puts them on the in-memory queue — returns 202 immediately.
    """
    raw_events = [e.model_dump() for e in request.events]
    await enqueue_events(project_id, raw_events)
    return IngestEventsResponse(
        received=len(raw_events),
        message="Events accepted for processing",
    )


# ── Query (dashboard-facing, JWT auth) ───────────────────────────────────────

def _default_from() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=7)


def _default_to() -> datetime:
    return datetime.now(timezone.utc)


async def _resolve_project(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verify the project exists and belongs to the current user."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get(
    "/analytics/projects/{project_id}/flags/{flag_key}",
    response_model=FlagAnalyticsResponse,
)
async def get_flag_timeseries(
    project_id: uuid.UUID,
    flag_key: str,
    from_time: datetime = Query(default_factory=_default_from),
    to_time: datetime = Query(default_factory=_default_to),
    granularity: Literal["hour", "day"] = Query(default="hour"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Time-series evaluation counts for a flag.

    Query params:
      from_time   — start of range (default: 7 days ago)
      to_time     — end of range (default: now)
      granularity — "hour" or "day" (default: "hour")

    Returns an array of buckets: { timestamp, variation, count }
    """
    await _resolve_project(project_id, current_user, db)

    service = AnalyticsService(db)
    result = await service.get_timeseries(
        project_id=project_id,
        flag_key=flag_key,
        from_time=from_time,
        to_time=to_time,
        granularity=granularity,
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Flag '{flag_key}' not found")

    return result


@router.get(
    "/analytics/projects/{project_id}/flags/{flag_key}/summary",
    response_model=FlagSummaryResponse,
)
async def get_flag_summary(
    project_id: uuid.UUID,
    flag_key: str,
    from_time: datetime = Query(default_factory=_default_from),
    to_time: datetime = Query(default_factory=_default_to),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Total evaluations + per-variation breakdown for a flag.

    Returns: { total_evaluations, variations: [{ variation, count, percentage }] }
    """
    await _resolve_project(project_id, current_user, db)

    service = AnalyticsService(db)
    result = await service.get_summary(
        project_id=project_id,
        flag_key=flag_key,
        from_time=from_time,
        to_time=to_time,
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Flag '{flag_key}' not found")

    return result