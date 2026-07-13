"""
Analytics ingestion endpoint — receives batches of evaluation events from the SDK.

Auth: API Key (same as /evaluate — SDK-facing)
Prefix: /api/v1

Why 202 Accepted?
  The hot path (evaluation) must never be slowed by analytics writes.
  We accept the batch, process it in the background, and return immediately.
  The SDK doesn't need to wait for DB confirmation.
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_project_from_api_key
from app.repositories.event_repo import EventRepository
from app.schemas.analytics import IngestEventsRequest, IngestEventsResponse

router = APIRouter()


async def _process_batch(
    db: AsyncSession,
    project_id: uuid.UUID,
    events: list[dict],
) -> None:
    """Background task — runs after 202 is returned to the SDK."""
    repo = EventRepository(db)
    await repo.ingest_batch(project_id, events)


@router.post(
    "/analytics/events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestEventsResponse,
)
async def ingest_events(
    request: IngestEventsRequest,
    background_tasks: BackgroundTasks,
    project_id: uuid.UUID = Depends(get_project_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a batch of evaluation events from the SDK.

    Accepts up to 500 events per request.
    Returns 202 immediately — aggregation happens in the background.
    Unknown flag keys are silently dropped.
    """
    raw_events = [e.model_dump() for e in request.events]

    background_tasks.add_task(
        _process_batch,
        db=db,
        project_id=project_id,
        events=raw_events,
    )

    return IngestEventsResponse(
        received=len(raw_events),
        message="Events accepted for processing",
    )