"""Persists Incident records AND their chat message thread to MongoDB,
falling back to a local JSONL file if MONGODB_URI isn't set, OR if Mongo is
unreachable when actually used (a network/TLS hiccup, an IP not in Atlas's
allowlist, etc.) -- a Mongo outage degrades to local storage instead of
crashing the chat. Both paths upsert by session_id, so storage is the
source of truth for resuming a session's history and Incident state across
process restarts.

Also auto-syncs each saved incident into Neo4j (if configured) right after
the Mongo save -- see _sync_to_neo4j -- so the fraud graph stays current
without needing a manual `python -m src.graph.neo4j_run` after every
conversation. Best-effort: a Neo4j hiccup never breaks saving the chat data
itself.

Same best-effort pattern for the geospatial hotspot/heatmap/deployment
build (see _sync_geospatial) -- a new victim_region shows up on the map
without a manual `python -m src.graph.geospatial_run`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.rag.incident import Incident

load_dotenv()

DB_NAME = "digital_arrest_shield"
COLLECTION_NAME = "incidents"
JSONL_FALLBACK_PATH = Path(__file__).resolve().parents[2] / "data" / "rag" / "incidents.jsonl"

# Short timeout so a dead Mongo/Neo4j fails fast instead of stalling every
# chat turn for a long default before falling back / giving up.
MONGO_TIMEOUT_MS = 5000
NEO4J_TIMEOUT_S = 5

_mongo_client: MongoClient | None = None
_mongo_checked = False

_neo4j_driver = None
_neo4j_checked = False


def _get_collection():
    global _mongo_client, _mongo_checked
    if not _mongo_checked:
        uri = os.environ.get("MONGODB_URI")
        if not uri:
            _mongo_checked = True  # no URI configured -- permanent for this process
            return None
        try:
            _mongo_client = MongoClient(
                uri, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS, connectTimeoutMS=MONGO_TIMEOUT_MS
            )
            _mongo_checked = True
        except PyMongoError:
            # Construction itself can fail (e.g. SRV DNS resolution) -- this
            # isn't cached as checked, so the next call tries again instead
            # of being stuck on jsonl forever if it was just transient.
            return None
    if _mongo_client is None:
        return None
    return _mongo_client[DB_NAME][COLLECTION_NAME]


def _read_jsonl_records() -> list[dict]:
    if not JSONL_FALLBACK_PATH.exists():
        return []
    records = []
    for line in JSONL_FALLBACK_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _upsert_jsonl(data: dict) -> None:
    JSONL_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = [r for r in _read_jsonl_records() if r.get("session_id") != data["session_id"]]
    records.append(data)
    JSONL_FALLBACK_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8"
    )


def _get_neo4j_driver():
    global _neo4j_driver, _neo4j_checked
    if not _neo4j_checked:
        uri = os.environ.get("NEO4J_URI")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")
        if not all([uri, username, password]):
            _neo4j_checked = True  # not configured -- permanent for this process
            return None
        try:
            _neo4j_driver = GraphDatabase.driver(
                uri, auth=(username, password), connection_timeout=NEO4J_TIMEOUT_S
            )
            _neo4j_checked = True
        except Exception:
            # Construction failure isn't cached as checked -- retry next
            # call in case it was transient, same pattern as Mongo above.
            return None
    return _neo4j_driver


def _sync_to_neo4j(data: dict) -> None:
    """Pushes this one incident into the Neo4j graph right after it's saved
    to Mongo, idempotently (see neo4j_load.push_single_incident) -- safe to
    call again as the same incident gains more fields over a conversation.
    Best-effort: any failure here is swallowed, never surfaced to the chat."""
    driver = _get_neo4j_driver()
    if driver is None:
        return
    try:
        from src.graph.neo4j_client import get_database
        from src.graph.neo4j_load import push_single_incident

        push_single_incident(driver, get_database(), data)
    except Exception:
        pass


def _sync_geospatial() -> None:
    """Rebuilds the geospatial hotspots/heatmap/deployment ranking from
    every incident currently in MongoDB, right after this save -- so a new
    victim_region from this conversation shows up on the map without
    needing a manual `python -m src.graph.geospatial_run`. Best-effort:
    any failure here is swallowed, never surfaced to the chat. Skipped
    entirely if Mongo isn't configured, since the rebuild reloads all
    incidents from there regardless of which path this save itself took."""
    if os.environ.get("MONGODB_URI") is None:
        return
    try:
        from src.graph.geospatial_pipeline import regenerate_geospatial_outputs

        regenerate_geospatial_outputs()
    except Exception:
        pass


def save_session(incident: Incident, messages: list[dict]) -> None:
    """Persists the Incident fields plus the full chat message thread, keyed
    by session_id. Once that's landed (Mongo or the jsonl fallback), also
    auto-syncs into Neo4j if configured (see _sync_to_neo4j) -- Mongo is the
    source of truth, Neo4j is a derived view pulled from it."""
    data = incident.model_dump(mode="json")
    data["messages"] = messages
    collection = _get_collection()
    if collection is not None:
        try:
            collection.update_one({"session_id": incident.session_id}, {"$set": data}, upsert=True)
            _sync_to_neo4j(data)
            _sync_geospatial()
            return
        except PyMongoError:
            pass  # Mongo configured but unreachable right now -- fall back below.
    _upsert_jsonl(data)
    _sync_to_neo4j(data)
    _sync_geospatial()


def load_session(session_id: str) -> tuple[Incident | None, list[dict]]:
    """Reconstructs the Incident and message thread for a session_id, or
    (None, []) if no prior record exists."""
    collection = _get_collection()
    doc = None
    if collection is not None:
        try:
            doc = collection.find_one({"session_id": session_id})
        except PyMongoError:
            doc = None  # Mongo configured but unreachable -- fall back to jsonl below.
            collection = None
    if collection is None:
        doc = next((r for r in _read_jsonl_records() if r.get("session_id") == session_id), None)

    if doc is None:
        return None, []

    messages = doc.get("messages", [])
    incident_fields = {k: v for k, v in doc.items() if k in Incident.model_fields}
    return Incident(**incident_fields), messages
