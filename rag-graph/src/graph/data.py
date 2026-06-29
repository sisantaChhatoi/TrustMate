"""Loads scam incidents from MongoDB for graph analysis."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

DB_NAME = "digital_arrest_shield"
COLLECTION_NAME = "incidents"


def load_incidents() -> list[dict]:
    """Returns every incident document, including the Mongo-only _id field
    (kept as-is; unused by the graph but harmless)."""
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not set. Add it to .env.")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    return list(client[DB_NAME][COLLECTION_NAME].find({}))
