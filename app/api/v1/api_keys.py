"""
API Key routes — generate, list, and revoke project API keys.

Auth: JWT Bearer (dashboard users only)
Prefix: /api/v1/projects/{project_id}/api-keys
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse
from app.services.api_key_service import APIKeyService

router = APIRouter()


@router.post("", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key(
    project_id: uuid.UUID,
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new API key for a project.

    IMPORTANT: The full key is returned ONLY in this response.
    It is not stored and cannot be retrieved again. Copy it immediately.
    """
    return await APIKeyService(db).generate(project_id, data, current_user.id)


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active API keys for a project (key prefix shown, not full key)."""
    return await APIKeyService(db).list(project_id, current_user.id)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    project_id: uuid.UUID,
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an API key. Any SDK using this key will immediately get 401 errors."""
    await APIKeyService(db).revoke(project_id, key_id, current_user.id)
