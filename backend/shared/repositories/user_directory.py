import re

from pymongo.asynchronous.database import AsyncDatabase


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def normalize_phone(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("+"):
        return "+" + _digits(raw)
    digits = _digits(raw)
    if digits.startswith("00"):
        return "+" + digits[2:]
    if len(digits) == 10:  # bare 10-digit → assume +91
        return "+91" + digits
    return "+" + digits


# in shared (not server.repositories) because the worker container has no server/
class UserDirectory:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["users"]

    async def user_id_for_phone(self, phone: str | None) -> str | None:
        if not phone:
            return None
        normalized = normalize_phone(phone)
        doc = await self._col.find_one(
            {"phone_no": normalized}, projection={"user_id": 1}
        )
        if doc is None:
            tail = _digits(normalized)[-10:]
            if len(tail) == 10:
                doc = await self._col.find_one(
                    {"phone_no": {"$regex": f"{tail}$"}}, projection={"user_id": 1}
                )
        return doc["user_id"] if doc else None
