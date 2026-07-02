import re
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


def _slugify(name: str) -> str:
    """Convert a project name into a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    slug: str | None = None  # auto-generated from name if not provided

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Project name cannot be blank")
        return v.strip()

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) or len(v) < 2:
            raise ValueError("Slug must be lowercase letters, numbers, and hyphens only")
        return v


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Project name cannot be blank")
        return v.strip() if v else v


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
