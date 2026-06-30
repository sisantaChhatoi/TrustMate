"""Persists geospatial intelligence (the heatmap HTML, hotspots, and
deployment ranking) to MongoDB -- same rationale as evidence_store.py: a
laptop can be lost, wiped, or have its repo cloned, but Mongo access is
controlled by who actually has the credentials. Local files in
data/graph/ are disposable exports of this exact same content, kept
because opening an HTML file in a browser is simpler than pulling it out
of Mongo first.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

DB_NAME = "digital_arrest_shield"
LATEST_COLLECTION = "geospatial_latest"
RUNS_COLLECTION = "geospatial_runs"
LATEST_DOC_ID = "latest"


def _get_db():
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not set. Add it to .env.")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    return client[DB_NAME]


def save_geospatial_snapshot(hotspots: list[dict], deployment_strategy: dict, heatmap_html: str) -> None:
    """Upserts the single 'latest' document (what a future dashboard/API
    would read) and inserts a timestamped history entry (so history isn't
    lost on the next overwrite, same as fraud_intelligence_runs)."""
    db = _get_db()
    generated_at = datetime.now(timezone.utc).isoformat()
    document = {
        "_id": LATEST_DOC_ID,
        "generated_at": generated_at,
        "hotspots": hotspots,
        "deployment_strategy": deployment_strategy,
        "heatmap_html": heatmap_html,
    }
    db[LATEST_COLLECTION].replace_one({"_id": LATEST_DOC_ID}, document, upsert=True)
    db[RUNS_COLLECTION].insert_one(
        {
            "generated_at": generated_at,
            "hotspot_count": len(hotspots),
            "top_deployment_zones": deployment_strategy.get("top_deployment_zones", []),
        }
    )


def load_latest_geospatial_snapshot() -> dict | None:
    return _get_db()[LATEST_COLLECTION].find_one({"_id": LATEST_DOC_ID})
