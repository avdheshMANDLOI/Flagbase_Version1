"""
Pydantic schemas for the analytics endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Ingestion schemas ─────────────────────────────────────────────────────────

class EvaluationEventItem(BaseModel):
    """A single evaluation event sent by the SDK."""
    flag_key: str
    variation: str
    user_key: str
    timestamp: Optional[datetime] = None


class IngestEventsRequest(BaseModel):
    """Batch of evaluation events from the SDK."""
    events: list[EvaluationEventItem] = Field(..., min_length=1, max_length=500)


class IngestEventsResponse(BaseModel):
    received: int
    message: str


# ── Query schemas ─────────────────────────────────────────────────────────────

class AnalyticsBucket(BaseModel):
    """A single time bucket — one hour or one day of data for one variation."""
    timestamp: datetime
    variation: str
    count: int


class FlagAnalyticsResponse(BaseModel):
    """Time-series response for a single flag."""
    flag_key: str
    from_time: datetime
    to_time: datetime
    granularity: str
    total_evaluations: int
    buckets: list[AnalyticsBucket]


class FlagSummaryVariation(BaseModel):
    variation: str
    count: int
    percentage: float


class FlagSummaryResponse(BaseModel):
    """Summary response — total impressions and variation breakdown."""
    flag_key: str
    from_time: datetime
    to_time: datetime
    total_evaluations: int
    variations: list[FlagSummaryVariation]