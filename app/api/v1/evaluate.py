"""
Evaluation route — the core SDK-facing endpoint.

Auth: API Key (not JWT — this is called by developer apps, not the dashboard)
Prefix: /api/v1

This is the most performance-critical endpoint in the entire system.
Every call to client.is_enabled() in user code hits this endpoint.

Flow:
  1. Validate API key → resolve project_id
  2. Evaluate flag (fetch from DB + run engine)
  3. Return result immediately
  4. Write evaluation_event asynchronously (BackgroundTask — after response is sent)
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_project_from_api_key
from app.repositories.event_repo import EventRepository
from app.schemas.flag import EvaluateRequest, EvaluateResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter()


async def _record_evaluation_event(
    db: AsyncSession,
    flag_id: uuid.UUID,
    user_id_hash: str,
    result: bool,
    reason: str,
) -> None:
    """
    Background task — writes the evaluation event AFTER the response is sent.

    Why BackgroundTasks instead of asyncio.create_task?
      BackgroundTasks is FastAPI-native and ties the task lifecycle to the
      request. For v1 fire-and-forget event recording it's the right tool.
      A proper task queue (Celery, ARQ) is overkill until v3.
    """
    repo = EventRepository(db)
    await repo.record_evaluation(
        flag_id=flag_id,
        user_id_hash=user_id_hash,
        result=result,
        reason=reason,
    )


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_flag(
    request: EvaluateRequest,
    background_tasks: BackgroundTasks,
    project_id: uuid.UUID = Depends(get_project_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluate a feature flag for a user.

    Called by the Python SDK (and any other SDK) on every is_enabled() call.
    Returns immediately. Event recording happens in the background.
    """
    service = EvaluationService(db)
    response, user_id_hash, flag_id = await service.evaluate(project_id, request)

    # Schedule event write — runs after this response is returned
    # Only record events for flags that actually exist
    if response.reason != "flag_not_found":
        background_tasks.add_task(
            _record_evaluation_event,
            db=db,
            flag_id=flag_id,
            user_id_hash=user_id_hash,
            result=response.enabled,
            reason=response.reason,
        )

    return response
