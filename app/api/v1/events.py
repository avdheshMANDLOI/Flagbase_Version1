"""
Events route — SDK conversion tracking endpoint.

Auth: API Key
Prefix: /api/v1

Called by client.track(event_name, user_id, flag_name, variant).
Used for A/B test conversion tracking (active in v4, stored from v1).
Returns 202 immediately — the DB write is async.
"""
import hashlib
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_project_from_api_key
from app.repositories.event_repo import EventRepository
from app.repositories.flag_repo import FlagRepository
from app.schemas.events import TrackEventRequest

router = APIRouter()


async def _record_conversion(
    db: AsyncSession,
    flag_id: uuid.UUID,
    user_id_hash: str,
    event_name: str,
    variant: str | None,
) -> None:
    repo = EventRepository(db)
    await repo.record_conversion(
        flag_id=flag_id,
        user_id_hash=user_id_hash,
        event_name=event_name,
        variant=variant,
    )


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def track_event(
    request: TrackEventRequest,
    background_tasks: BackgroundTasks,
    project_id: uuid.UUID = Depends(get_project_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a conversion event from the SDK.

    Returns 202 immediately. The DB write happens in the background.
    If the flag doesn't exist, we silently drop the event (don't error the caller).
    """
    flag_repo = FlagRepository(db)
    flag = await flag_repo.get_by_name(project_id, request.flag_name)

    if flag:
        user_id_hash = hashlib.sha256(request.user_id.encode()).hexdigest()
        background_tasks.add_task(
            _record_conversion,
            db=db,
            flag_id=flag.id,
            user_id_hash=user_id_hash,
            event_name=request.event_name,
            variant=request.variant,
        )

    return {"message": "Event received"}
