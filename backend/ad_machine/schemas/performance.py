from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class CreativePerformance(BaseModel):
    performance_id: str
    pairing_id: str
    platform: str
    impressions: int
    clicks: int
    ctr: float
    conversions: int | None = None
    cpa: float | None = None
    spend: float
    days_running: int
    user_label: Literal["winner", "loser", "neutral"] | None = None
    user_notes: str | None = None
    uploaded_at: datetime
