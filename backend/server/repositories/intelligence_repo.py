from pymongo.asynchronous.database import AsyncDatabase

# Snapshot docs written by the `python -m server.graph` batch job.
from server.graph.pipeline import INTELLIGENCE_COLLECTION


class IntelligenceRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db[INTELLIGENCE_COLLECTION]

    async def _get(self, kind: str) -> dict | None:
        return await self._col.find_one({"_id": kind})

    async def rings(self) -> dict:
        doc = await self._get("rings")
        return doc or {"rings": [], "generated_at": None}

    async def geospatial(self) -> dict:
        doc = await self._get("geospatial")
        return doc or {
            "hotspots": [],
            "deployment_strategy": {},
            "generated_at": None,
        }

    async def accounts(self) -> dict:
        doc = await self._get("account_intelligence")
        return doc or {"accounts": [], "generated_at": None}
