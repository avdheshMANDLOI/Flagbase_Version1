import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Use Postgres JSONB in production, fall back to generic JSON in SQLite for tests.
# Both store/retrieve Python dicts and lists identically at the ORM layer.
_JSONType = JSONB().with_variant(JSON(), "sqlite")


class FlagRule(Base):
    """
    Targeting rule attached to a flag.

    v1 scope note: `operator` supports 'equals', 'not_equals', 'in_list',
    'not_in_list' at the application layer. 'contains' and numeric/range
    operators are v2. The column is left as a free-form string (not a DB
    enum) specifically so v2 can add operators without a schema migration
    — only the application-layer validation in app/schemas needs to change.
    See SPEC.md Section 2.5 and Section 11.2.
    """

    __tablename__ = "flag_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flags.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    attribute_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operator: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[dict | list | str] = mapped_column(_JSONType, nullable=False)
    effect: Mapped[str] = mapped_column(String(10), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    flag: Mapped["Flag"] = relationship(back_populates="rules")
