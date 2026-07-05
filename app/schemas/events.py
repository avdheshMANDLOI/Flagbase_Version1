"""
Pydantic schemas for the SDK event tracking endpoint.
"""
from pydantic import BaseModel


class TrackEventRequest(BaseModel):
    event_name: str
    user_id: str
    flag_name: str
    variant: str | None = None
