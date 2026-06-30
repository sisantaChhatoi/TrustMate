"""Read-only fraud-intelligence API, served from the precomputed snapshots."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from server.deps import get_db
from server.repositories.intelligence_repo import IntelligenceRepository

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

_RISK_RANK = {"high": 2, "medium": 1, "low": 0}


def get_intelligence_repository(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> IntelligenceRepository:
    return IntelligenceRepository(db)


_RepoDep = Annotated[IntelligenceRepository, Depends(get_intelligence_repository)]


@router.get("/rings")
async def fraud_rings(repo: _RepoDep) -> dict:
    """Detected fraud rings (entity clusters that co-occur across incidents),
    largest first."""
    return await repo.rings()


@router.get("/hotspots")
async def hotspots(repo: _RepoDep) -> dict:
    """Geocoded fraud hotspots and the patrol-deployment ranking."""
    data = await repo.geospatial()
    return {
        "generated_at": data.get("generated_at"),
        "hotspots": data.get("hotspots", []),
        "deployment_strategy": data.get("deployment_strategy", {}),
    }


@router.get("/high-risk-accounts")
async def high_risk_accounts(repo: _RepoDep, min_risk: str = "medium") -> dict:
    """Entities (accounts / numbers / UPI) reused across enough incidents to
    flag. `min_risk` is one of low / medium / high."""
    data = await repo.accounts()
    floor = _RISK_RANK.get(min_risk, 1)
    accounts = [
        a
        for a in data.get("accounts", [])
        # regions are graph nodes too, but they aren't payable entities
        if a.get("type") != "victim_region"
        and _RISK_RANK.get(a.get("risk_level"), 0) >= floor
    ]
    return {"generated_at": data.get("generated_at"), "accounts": accounts}
