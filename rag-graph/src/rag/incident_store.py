"""Persists Incident records AND their chat message thread to MongoDB,
falling back to a local JSONL file if MONGODB_URI isn't set, OR if Mongo is
unreachable when actually used (a network/TLS hiccup, an IP not in Atlas's
allowlist, etc.) -- a Mongo outage degrades to local storage instead of
crashing the chat. Both paths upsert by session_id, so storage is the
source of truth for resuming a session's history and Incident state across
process restarts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.rag.incident import Incident

load_dotenv()

DB_NAME = "digital_arrest_shield"
COLLECTION_NAME = "incidents"
JSONL_FALLBACK_PATH = Path(__file__).resolve().parents[2] / "data" / "rag" / "incidents.jsonl"

# Short timeout so a dead Mongo fails fast instead of stalling every chat
# turn for the ~30s pymongo default before falling back.
MONGO_TIMEOUT_MS = 5000

_mongo_client: MongoClient | None = None
_mongo_checked = False


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


def save_session(incident: Incident, messages: list[dict]) -> None:
    """Persists the Incident fields plus the full chat message thread, keyed
    by session_id."""
    data = incident.model_dump(mode="json")
    data["messages"] = messages
    collection = _get_collection()
    if collection is not None:
        try:
            collection.update_one({"session_id": incident.session_id}, {"$set": data}, upsert=True)
            return
        except PyMongoError:
            pass  # Mongo configured but unreachable right now -- fall back below.
    _upsert_jsonl(data)


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
