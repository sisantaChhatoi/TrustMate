import re

from pymongo.asynchronous.database import AsyncDatabase


# in shared (not server.repositories) because the worker container has no server/
class UserDirectory:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["users"]

    async def user_id_for_phone(self, phone: str | None) -> str | None:
        if not phone:
            return None
        # match on the last 10 digits — neither caller-ID nor stored phone_no
        # is guaranteed to carry the same +91/0 prefix
        tail = re.sub(r"\D", "", phone)[-10:]
        if len(tail) < 10:
            return None
        doc = await self._col.find_one(
            {"phone_no": {"$regex": f"{tail}$"}}, projection={"user_id": 1}
        )
        return doc["user_id"] if doc else None
