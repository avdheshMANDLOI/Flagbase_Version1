"""
API Key repository — all SQLAlchemy queries for API keys.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey


class APIKeyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        """
        Look up an API key by its SHA-256 hash.
        Used on every SDK request to validate the key.
        """
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, key_id: uuid.UUID) -> APIKey | None:
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: uuid.UUID) -> list[APIKey]:
        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.project_id == project_id, APIKey.is_active == True)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        project_id: uuid.UUID,
        label: str,
        key_hash: str,
        key_prefix: str,
    ) -> APIKey:
        api_key = APIKey(
            project_id=project_id,
            label=label,
            key_hash=key_hash,
            key_prefix=key_prefix,
        )
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)
        return api_key

    async def revoke(self, api_key: APIKey) -> None:
        """Soft delete — sets is_active=False."""
        api_key.is_active = False
        await self.db.commit()
