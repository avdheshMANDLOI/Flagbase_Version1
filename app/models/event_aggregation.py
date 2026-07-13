"""
EventAggregation — pre-aggregated hourly rollup of flag evaluations.

Why pre-aggregate?
  Storing raw events and grouping at query time doesn't scale.
  A flag evaluated 1M times requires scanning 1M rows per query.
  Pre-aggregating into hourly buckets means queries are O(1)
  regardless of event volume — same approach used by Datadog and Grafana.
"""
from datetime import datetime

import uuid
from sqlalchemy import BigInteger, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class EventAggregation(Base):
    __tablename__ = "event_aggregations"
    __table_args__ = (
        UniqueConstraint("flag_id", "hour", "variation", name="uq_event_agg_flag_hour_variation"),
        Index("idx_event_agg_flag_id_hour", "flag_id", "hour"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    # Truncated to the hour — e.g. 2026-07-12 14:00:00+00
    hour: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # "true", "false", or a variant name like "blue" / "control"
    variation: Mapped[str] = mapped_column(String(50), nullable=False)
    count: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), nullable=False, default=0)