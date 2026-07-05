from datetime import datetime

from pydantic import BaseModel


class Notification(BaseModel):
    user_id: str
    confidence: float
    reason: str
    red_flags: list[str]
    sent_at: datetime
