"""Cypher-based fraud pattern queries against the Neo4j graph.

Community/ring detection (Louvain) is NOT done here -- Neo4j Aura's free
tier doesn't include the Graph Data Science plugin those procedures need.
full_edge_list() pulls the graph back out so ring detection can run via the
same NetworkX Louvain logic the local (non-Neo4j) graph module already uses
-- see neo4j_run.py.
"""

from __future__ import annotations

import networkx as nx
from neo4j import Driver

TYPE_MAP = {
    "MuleAccount": "mule_account",
    "PhoneNumber": "phone_number",
    "VictimRegion": "victim_region",
    "ScammerId": "scammer_id",
}


def high_degree_accounts(driver: Driver, database: str) -> list[dict]:
    """Mule accounts reused across the most incidents -- the core
    infrastructure of a coordinated operation, not a one-off scam."""
    query = """
        MATCH (a:MuleAccount)
        OPTIONAL MATCH (a)-[:USED_IN_CALL_WITH]->(p:PhoneNumber)
        RETURN a.value AS account, a.incident_count AS incident_count,
               count(DISTINCT p) AS distinct_phone_numbers,
               collect(DISTINCT p.value) AS phone_numbers
        ORDER BY incident_count DESC
    """
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(query)]


def regional_hotspots(driver: Driver, database: str) -> list[dict]:
    """Victim regions hit by the most distinct phone numbers/incidents."""
    query = """
        MATCH (r:VictimRegion)
        OPTIONAL MATCH (p:PhoneNumber)-[:TARGETED_REGION]->(r)
        RETURN r.value AS region, r.incident_count AS incident_count,
               count(DISTINCT p) AS distinct_phone_numbers,
               collect(DISTINCT p.value) AS phone_numbers
        ORDER BY incident_count DESC
    """
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(query)]


def multi_region_accounts(driver: Driver, database: str) -> list[dict]:
    """Mule accounts whose linked phone number(s) targeted victims in more
    than one distinct region -- a direct signal of the same operation
    running across multiple areas (jurisdiction overlap), before any
    state-mapping is applied in Python."""
    query = """
        MATCH (a:MuleAccount)-[:USED_IN_CALL_WITH]->(p:PhoneNumber)-[:TARGETED_REGION]->(r:VictimRegion)
        WITH a, collect(DISTINCT r.value) AS regions
        WHERE size(regions) > 1
        RETURN a.value AS mule_account, regions
        ORDER BY size(regions) DESC
    """
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(query)]


def shared_account_pairs(driver: Driver, database: str) -> list[dict]:
    """Mule accounts linked via a shared phone number -- a direct signal
    that two seemingly-different accounts are probably the same operation."""
    query = """
        MATCH (a1:MuleAccount)-[:USED_IN_CALL_WITH]->(p:PhoneNumber)<-[:USED_IN_CALL_WITH]-(a2:MuleAccount)
        WHERE a1.value < a2.value
        RETURN DISTINCT a1.value AS account_1, a2.value AS account_2, p.value AS shared_phone_number
    """
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(query)]


def full_edge_list(driver: Driver, database: str) -> list[dict]:
    """Every relationship in the graph, for rebuilding a NetworkX graph and
    running Louvain community detection in Python."""
    query = """
        MATCH (a)-[rel]->(b)
        RETURN labels(a)[0] AS from_type, a.value AS from_value,
               labels(b)[0] AS to_type, b.value AS to_value,
               type(rel) AS rel_type, rel.incident_count AS weight,
               rel.incident_ids AS incident_ids
    """
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(query)]


def all_nodes(driver: Driver, database: str) -> list[dict]:
    """Every node with its first_seen/last_seen timestamps -- used to fill
    in "operational_since" style fields without guessing at a date."""
    query = """
        MATCH (n)
        RETURN labels(n)[0] AS node_type, n.value AS value,
               n.incident_count AS incident_count,
               n.first_seen AS first_seen, n.last_seen AS last_seen
    """
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(query)]


def rebuild_networkx_graph(edges: list[dict]) -> nx.Graph:
    """Reconstructs a graph with the same node/edge attribute shape
    src/graph/analyze.py expects (type, value, incident_ids, weight), so
    Louvain/ring-building/account-intelligence can run unmodified on data
    that came from Neo4j instead of the in-memory build.py path."""
    graph = nx.Graph()
    for edge in edges:
        from_type = TYPE_MAP.get(edge["from_type"], edge["from_type"])
        to_type = TYPE_MAP.get(edge["to_type"], edge["to_type"])
        from_id = f"{from_type}:{edge['from_value']}"
        to_id = f"{to_type}:{edge['to_value']}"
        incident_ids = edge.get("incident_ids") or []

        for node_id, node_type, node_value in (
            (from_id, from_type, edge["from_value"]),
            (to_id, to_type, edge["to_value"]),
        ):
            if not graph.has_node(node_id):
                graph.add_node(node_id, type=node_type, value=node_value, incident_ids=[])
            graph.nodes[node_id]["incident_ids"] = sorted(set(graph.nodes[node_id]["incident_ids"]) | set(incident_ids))

        weight = edge.get("weight") or 1
        if graph.has_edge(from_id, to_id):
            graph[from_id][to_id]["weight"] += weight
            graph[from_id][to_id]["incident_ids"] = sorted(set(graph[from_id][to_id]["incident_ids"]) | set(incident_ids))
        else:
            graph.add_edge(from_id, to_id, weight=weight, incident_ids=sorted(set(incident_ids)))
    return graph
