"""
Analytics ingestion endpoint — receives batches of evaluation events from the SDK.

Auth: API Key (same as /evaluate — SDK-facing)
Prefix: /api/v1

Why 202 Accepted?
  The hot path must never be slowed by analytics writes.
  Events go onto the in-memory queue and return immediately.
  The background worker picks them up and writes to DB.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_project_from_api_key
from app.core.event_queue import enqueue_events
from app.schemas.analytics import IngestEventsRequest, IngestEventsResponse

router = APIRouter()


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

    Accepts up to 500 events per request.
    Puts them on the in-memory queue — returns 202 immediately.
    The event worker picks them up and aggregates into DB.
    Unknown flag keys are silently dropped by the worker.
    """
    raw_events = [e.model_dump() for e in request.events]
    await enqueue_events(project_id, raw_events)
    return IngestEventsResponse(
        received=len(raw_events),
        message="Events accepted for processing",
    )