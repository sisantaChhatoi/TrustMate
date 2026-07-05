from datetime import datetime

from pydantic import BaseModel


class CallRecord(BaseModel):
    room_name: str
    user_phone: str | None = None
    user_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    last_notified_at: datetime | None = None
