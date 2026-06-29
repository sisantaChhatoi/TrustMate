"""Persists fraud-ring intelligence AND the actual evidence report content
(the .txt report, network diagram, jurisdiction summary, summary
statistics) to MongoDB -- the durable, access-controlled copy. Local files
(court_evidence_packages/, summary_statistics.txt, etc.) are disposable
exports for quick reading built from this exact same content; this is the
real one, since a laptop can be lost, wiped, or have its repo cloned, but
Atlas access is controlled by who actually has the credentials.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

from src.graph.court_reports import (
    build_evidence_report_text,
    build_inter_jurisdiction_alert,
    build_jurisdiction_summary,
    build_network_diagram,
    build_summary_statistics_text,
)

load_dotenv()

DB_NAME = "digital_arrest_shield"
RINGS_COLLECTION = "fraud_rings"
RUNS_COLLECTION = "fraud_intelligence_runs"


def _get_db():
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not set. Add it to .env.")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    return client[DB_NAME]


def save_ring_intelligence(rings: list[dict]) -> None:
    """Upserts each ring by fraud_ring_id, INCLUDING the rendered evidence
    report text and supporting JSON content -- not just the structured
    data -- so the actual court-evidence-package content lives in Mongo,
    not only as local files."""
    collection = _get_db()[RINGS_COLLECTION]
    generated_at = datetime.now(timezone.utc).isoformat()
    for ring in rings:
        document = {
            **ring,
            "detailed_evidence_report_text": build_evidence_report_text(ring),
            "network_diagram": build_network_diagram(ring),
            "jurisdiction_summary": build_jurisdiction_summary(ring),
            "generated_at": generated_at,
        }
        collection.update_one(
            {"fraud_ring_id": ring["fraud_ring_id"]},
            {"$set": document},
            upsert=True,
        )


def save_run_summary(rings: list[dict], total_incidents: int) -> None:
    """Stores the overall summary_statistics text and inter-jurisdiction
    alert content from this run -- one document per run, timestamped, so
    history isn't lost on each rerun the way local-file overwrites would."""
    collection = _get_db()[RUNS_COLLECTION]
    collection.insert_one(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_incidents": total_incidents,
            "total_rings": len(rings),
            "summary_statistics_text": build_summary_statistics_text(rings, total_incidents),
            "inter_jurisdiction_alert": build_inter_jurisdiction_alert(rings),
        }
    )


def load_ring_intelligence() -> list[dict]:
    """Reads back whatever's currently stored, e.g. for a future dashboard
    or API instead of reading local files."""
    return list(_get_db()[RINGS_COLLECTION].find({}, {"_id": 0}))


def load_latest_run_summary() -> dict | None:
    return _get_db()[RUNS_COLLECTION].find_one({}, {"_id": 0}, sort=[("generated_at", -1)])
