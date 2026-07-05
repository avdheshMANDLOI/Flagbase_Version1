"""
Pydantic schemas for API key routes.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    label: str = "Default"


class APIKeyResponse(BaseModel):
    """
    Used for listing keys — key_prefix shown (e.g. proj_sk_ab12),
    never the full plaintext key.
    """
    id: uuid.UUID
    project_id: uuid.UUID
    label: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(BaseModel):
    """
    Returned ONLY at creation time. Contains the full plaintext key.
    This is the only time the full key is ever visible.
    """
    id: uuid.UUID
    project_id: uuid.UUID
    label: str
    key: str          # full plaintext — shown once, never stored
    key_prefix: str
    created_at: datetime

    model_config = {"from_attributes": True}
