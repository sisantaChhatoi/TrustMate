"""Neo4j Aura connection helper."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

load_dotenv()


def get_driver() -> Driver:
    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    if not all([uri, username, password]):
        raise RuntimeError("NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD not set. Add them to .env.")
    return GraphDatabase.driver(uri, auth=(username, password))


def get_database() -> str:
    return os.environ.get("NEO4J_DATABASE", "neo4j")
