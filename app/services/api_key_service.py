"""
API Key service — generate, list, and revoke project API keys.

Security design:
  - Plaintext key is generated with secrets.token_hex (cryptographically secure)
  - Only the SHA-256 hash is stored in the database
  - The plaintext key is returned ONCE at creation and never stored
  - On every SDK request, the incoming key is hashed and compared to stored hashes

Key format: proj_sk_<64 hex chars>
  - "proj_sk_" prefix makes keys identifiable in logs and easy to grep if leaked
  - 32 random bytes (64 hex chars) = 256 bits of entropy
"""
import hashlib
import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.api_key_repo import APIKeyRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.api_key import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse

API_KEY_PREFIX = "proj_sk_"


def _generate_raw_key() -> str:
    """Generate a cryptographically secure plaintext API key."""
    return API_KEY_PREFIX + secrets.token_hex(32)


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key. This is what gets stored."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def extract_prefix(raw_key: str) -> str:
    """
    Return the first 20 chars of the key as a display prefix.
    e.g. "proj_sk_ab12ef34..." → "proj_sk_ab12ef34..."[:20]
    Used in the list endpoint so users can identify their keys.
    """
    return raw_key[:20]


class APIKeyService:
    def __init__(self, db: AsyncSession):
        self.repo = APIKeyRepository(db)
        self.project_repo = ProjectRepository(db)

    async def generate(
        self, project_id: uuid.UUID, data: APIKeyCreate, owner_id: uuid.UUID
    ) -> APIKeyCreatedResponse:
        await self._assert_project_ownership(project_id, owner_id)

        raw_key = _generate_raw_key()
        key_hash = hash_api_key(raw_key)
        key_prefix = extract_prefix(raw_key)

        api_key = await self.repo.create(
            project_id=project_id,
            label=data.label,
            key_hash=key_hash,
            key_prefix=key_prefix,
        )

        # Return the full plaintext key — only time it will ever be visible
        return APIKeyCreatedResponse(
            id=api_key.id,
            project_id=api_key.project_id,
            label=api_key.label,
            key=raw_key,
            key_prefix=api_key.key_prefix,
            created_at=api_key.created_at,
        )

    async def list(
        self, project_id: uuid.UUID, owner_id: uuid.UUID
    ) -> list[APIKeyResponse]:
        await self._assert_project_ownership(project_id, owner_id)
        keys = await self.repo.list_by_project(project_id)
        return [APIKeyResponse.model_validate(k) for k in keys]

    async def revoke(
        self, project_id: uuid.UUID, key_id: uuid.UUID, owner_id: uuid.UUID
    ) -> None:
        await self._assert_project_ownership(project_id, owner_id)
        api_key = await self.repo.get_by_id(key_id)
        if not api_key or api_key.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )
        await self.repo.revoke(api_key)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _assert_project_ownership(
        self, project_id: uuid.UUID, owner_id: uuid.UUID
    ) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if not project or not project.is_active or project.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
