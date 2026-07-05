"""
FastAPI dependencies shared across routes.

Two auth flows:
  1. JWT Bearer   → get_current_user  (dashboard routes — human users)
  2. API Key      → get_project_from_api_key  (SDK evaluation route — machine clients)
"""
import hashlib
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.api_key import APIKey
from app.models.user import User
from app.repositories.api_key_repo import APIKeyRepository
from app.repositories.user_repo import UserRepository

bearer_scheme = HTTPBearer()


# ── JWT dependency (dashboard routes) ────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that:
    1. Extracts the Bearer token from the Authorization header
    2. Decodes and validates the JWT
    3. Fetches the user from DB
    4. Raises 401 if anything is wrong

    Usage:  current_user: User = Depends(get_current_user)
    """
    token = credentials.credentials
    user_id_str = decode_access_token(token)

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    return user


# ── API Key dependency (SDK evaluation route) ─────────────────────────────────

async def get_project_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """
    Dependency for SDK-facing routes (POST /evaluate, POST /events).

    Extracts the API key from the Authorization: Bearer header,
    hashes it with SHA-256, and looks it up in the api_keys table.

    Returns the project_id associated with the key.
    Raises 401 if the key is invalid or revoked.

    Why SHA-256 (not bcrypt)?
      API keys are 256-bit random strings — they don't need bcrypt's
      computational cost factor. SHA-256 is fast and sufficient here.
      Bcrypt is needed for passwords because humans choose weak passwords
      and attackers can use rainbow tables. Random tokens don't have this problem.
    """
    raw_key = credentials.credentials
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    repo = APIKeyRepository(db)
    api_key = await repo.get_by_hash(key_hash)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    return api_key.project_id
