from pymongo.asynchronous.database import AsyncDatabase

from server.models.incident import Incident


class IncidentRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["incidents"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("session_id", unique=True)

    async def get(self, session_id: str) -> Incident | None:
        doc = await self._col.find_one({"session_id": session_id})
        return Incident(**doc) if doc else None

    async def upsert(self, incident: Incident) -> None:
        await self._col.update_one(
            {"session_id": incident.session_id},
            {"$set": incident.model_dump(mode="json")},
            upsert=True,
        )

    async def lookup_entity(
        self, value: str, exclude_session: str | None = None
    ) -> dict:
        """How often a phone/account/UPI value appears across *other* reported
        incidents, what it was seen as, and the entities it co-occurs with."""
        value = value.strip()
        query: dict = {
            "$or": [
                {"caller_number": value},
                {"mule_account": value},
                {"mule_upi": value},
            ]
        }
        if exclude_session is not None:
            query = {"$and": [query, {"session_id": {"$ne": exclude_session}}]}

        seen_as: set[str] = set()
        scam_types: set[str] = set()
        linked: dict[str, set[str]] = {
            "caller_number": set(),
            "mule_account": set(),
            "mule_upi": set(),
            "victim_region": set(),
        }
        count = 0
        async for doc in self._col.find(query):
            count += 1
            for role in ("caller_number", "mule_account", "mule_upi"):
                if doc.get(role) == value:
                    seen_as.add(role)
            for field, bucket in linked.items():
                other = doc.get(field)
                if other and other != value:
                    bucket.add(other)
            if doc.get("scam_type"):
                scam_types.add(doc["scam_type"])

        return {
            "value": value,
            "report_count": count,
            "seen_as": sorted(seen_as),
            "scam_types": sorted(scam_types),
            "linked_entities": {k: sorted(v) for k, v in linked.items() if v},
        }
