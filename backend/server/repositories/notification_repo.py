from pymongo.asynchronous.database import AsyncDatabase

from server.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["notifications"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index([("user_id", 1), ("sent_at", -1)])

    async def insert(self, notification: Notification) -> None:
        await self._col.insert_one(notification.model_dump())

    async def list_for_user(self, user_id: str, limit: int = 50) -> list[Notification]:
        cursor = self._col.find({"user_id": user_id}).sort("sent_at", -1).limit(limit)
        return [Notification(**doc) async for doc in cursor]
