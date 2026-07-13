"""
Pydantic schemas for the analytics ingestion endpoint.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EvaluationEventItem(BaseModel):
    """A single evaluation event sent by the SDK."""
    flag_key: str
    variation: str                    # "true" / "false" / variant name
    user_key: str
    timestamp: Optional[datetime] = None   # SDK sends its own timestamp; falls back to server time


class IngestEventsRequest(BaseModel):
    """Batch of evaluation events from the SDK."""
    events: list[EvaluationEventItem] = Field(..., min_length=1, max_length=500)


class IngestEventsResponse(BaseModel):
    received: int
    message: str