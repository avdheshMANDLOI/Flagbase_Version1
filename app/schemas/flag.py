"""
Pydantic schemas for flag routes and evaluation endpoint.
"""
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class FlagCreate(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    rollout_percentage: int = 0

    @field_validator("name")
    @classmethod
    def name_must_be_slug(cls, v: str) -> str:
        """
        Flag names are used as identifiers in code (e.g. is_enabled("new_checkout")).
        They must be lowercase, alphanumeric, hyphens, or underscores only.
        """
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "Flag name must contain only lowercase letters, numbers, underscores, or hyphens"
            )
        return v

    @field_validator("rollout_percentage")
    @classmethod
    def rollout_in_range(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("rollout_percentage must be between 0 and 100")
        return v


class FlagUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    is_enabled: bool | None = None
    rollout_percentage: int | None = None

    @field_validator("rollout_percentage")
    @classmethod
    def rollout_in_range(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("rollout_percentage must be between 0 and 100")
        return v


class FlagResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    is_enabled: bool
    rollout_percentage: int
    flag_type: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlagListResponse(BaseModel):
    flags: list[FlagResponse]
    total: int
    page: int


# ── Evaluation schemas ────────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    flag_name: str
    user_id: str
    context: dict | None = None


class EvaluateResponse(BaseModel):
    enabled: bool
    variant: str | None
    reason: str
    flag_name: str
