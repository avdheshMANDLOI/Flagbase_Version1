"""
Evaluation service — orchestrates the full evaluation flow.

This service:
  1. Fetches the flag and its rules from the DB
  2. Calls the pure evaluation engine
  3. Returns the result (event recording is handled by the router via BackgroundTask)

It does NOT write events itself — that is the router's job, keeping this
service pure and easy to test.
"""
import hashlib
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.flag_repo import FlagRepository
from app.schemas.flag import EvaluateRequest, EvaluateResponse
from app.services import evaluation_engine


def _hash_user_id(user_id: str) -> str:
    """
    SHA-256 hash of the user_id for privacy.
    We store the hash in evaluation_events, never the raw user_id.
    See SPEC.md Section 3.4.
    """
    return hashlib.sha256(user_id.encode()).hexdigest()


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.flag_repo = FlagRepository(db)

    async def evaluate(
        self, project_id: uuid.UUID, request: EvaluateRequest
    ) -> tuple[EvaluateResponse, str, uuid.UUID]:
        """
        Evaluate a flag for a user.

        Returns:
            (EvaluateResponse, user_id_hash, flag_id)
            The caller (router) uses user_id_hash and flag_id to record the event.
        """
        flag = await self.flag_repo.get_by_name(project_id, request.flag_name)

        if flag is None:
            # Never throw 500 for a missing flag — return safe default
            # This matches SDK graceful degradation behaviour (SPEC.md Section 3.3)
            return (
                EvaluateResponse(
                    enabled=False,
                    variant=None,
                    reason="flag_not_found",
                    flag_name=request.flag_name,
                ),
                _hash_user_id(request.user_id),
                uuid.uuid4(),  # placeholder — no event will be written for missing flags
            )

        result = evaluation_engine.evaluate(
            flag=flag,
            rules=flag.rules,
            user_id=request.user_id,
            context=request.context,
        )

        response = EvaluateResponse(
            enabled=result.enabled,
            variant=result.variant,
            reason=result.reason,
            flag_name=request.flag_name,
        )

        return response, _hash_user_id(request.user_id), flag.id
