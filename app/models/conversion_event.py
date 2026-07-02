from datetime import datetime
import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConversionEvent(Base):
    """
    v1 scope note: the SDK's track() method writes here from day one (see
    SPEC.md Section 13.1). Not read from until v4 (A/B test conversion
    metrics).
    """

    __tablename__ = "conversion_events"
    __table_args__ = (
        Index("idx_conversion_events_flag_id_event_name", "flag_id", "event_name"),
        Index("idx_conversion_events_ab_test_id", "ab_test_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flags.id"), nullable=False
    )
    ab_test_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ab_tests.id"), nullable=True
    )
    user_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
