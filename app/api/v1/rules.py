"""
Targeting rule routes — add and remove rules for a flag.

Auth: JWT Bearer
Prefix: /api/v1/flags/{flag_id}/rules
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleResponse
from app.services.rule_service import RuleService

router = APIRouter()


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    flag_id: uuid.UUID,
    data: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a targeting rule to a flag."""
    return await RuleService(db).create(flag_id, data, current_user.id)


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    flag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all targeting rules for a flag, sorted by priority."""
    return await RuleService(db).list(flag_id, current_user.id)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    flag_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a targeting rule."""
    await RuleService(db).delete(flag_id, rule_id, current_user.id)
