from datetime import datetime
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EvaluationEvent(Base):
    """
    v1 scope note: written to from day one — the evaluation engine's core
    flow includes writing this event (see SPEC.md Section 11.1). It is not
    *read* from until v3 (analytics dashboards) or v4 (A/B test results).
    """

    __tablename__ = "evaluation_events"
    __table_args__ = (
        Index("idx_eval_events_flag_id_timestamp", "flag_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flags.id", ondelete="CASCADE"), nullable=False
    )
    user_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ab_test_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
