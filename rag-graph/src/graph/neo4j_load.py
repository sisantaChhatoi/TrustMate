"""Pushes incidents into Neo4j Aura as a property graph: MuleAccount,
PhoneNumber, VictimRegion, and ScammerId (the UPI handle a victim was asked
to pay) nodes, linked by USED_IN_CALL_WITH, TARGETED_REGION, and
REQUESTED_PAYMENT_VIA relationships. incident_count is how reuse shows up
-- the same account/number/UPI appearing across multiple incidents
increments it.

Idempotent per incident_id: every node/relationship tracks which
incident_ids have already been counted, and only increments
incident_count the first time a given incident_id is seen for it. This is
what makes it safe to call repeatedly for the SAME incident as a
conversation progresses (see src/rag/incident_store.py's auto-sync) without
double-counting -- amount_requested/timestamp still always refresh to the
latest known value, only the counting is one-shot per incident.
"""

from __future__ import annotations

from neo4j import Driver


def _normalize(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_NODE_QUERY = """
MERGE (n:{label} {{value: $value}})
ON CREATE SET n.incident_count = 0, n.incident_ids = [], n.first_seen = $timestamp
SET n.last_seen = $timestamp
WITH n
WHERE NOT $incident_id IN n.incident_ids
SET n.incident_count = n.incident_count + 1, n.incident_ids = n.incident_ids + $incident_id
"""


def _merge_node(tx, label: str, value: str, incident_id: str, timestamp) -> None:
    tx.run(_NODE_QUERY.format(label=label), value=value, incident_id=incident_id, timestamp=timestamp)


_REL_QUERY = """
MATCH (a:{from_label} {{value: $from_value}}), (b:{to_label} {{value: $to_value}})
MERGE (a)-[rel:{rel_type}]->(b)
ON CREATE SET rel.incident_count = 0, rel.incident_ids = []
SET rel.amount_requested = $amount, rel.timestamp = $timestamp
WITH rel
WHERE NOT $incident_id IN rel.incident_ids
SET rel.incident_count = rel.incident_count + 1, rel.incident_ids = rel.incident_ids + $incident_id
"""


def _merge_relationship(
    tx, from_label: str, from_value: str, to_label: str, to_value: str, rel_type: str, incident_id: str, amount, timestamp
) -> None:
    tx.run(
        _REL_QUERY.format(from_label=from_label, to_label=to_label, rel_type=rel_type),
        from_value=from_value,
        to_value=to_value,
        incident_id=incident_id,
        amount=amount,
        timestamp=timestamp,
    )


def _push_incident(tx, incident: dict) -> None:
    incident_id = incident.get("incident_id") or str(incident.get("_id"))
    mule_account = _normalize(incident.get("mule_account"))
    phone_number = _normalize(incident.get("caller_number"))
    victim_region = _normalize(incident.get("victim_region"))
    scammer_id = _normalize(incident.get("mule_upi"))
    amount_requested = _safe_float(incident.get("amount_demanded"))
    timestamp = incident.get("timestamp")

    if mule_account:
        _merge_node(tx, "MuleAccount", mule_account, incident_id, timestamp)
    if phone_number:
        _merge_node(tx, "PhoneNumber", phone_number, incident_id, timestamp)
    if victim_region:
        _merge_node(tx, "VictimRegion", victim_region, incident_id, timestamp)
    if scammer_id:
        _merge_node(tx, "ScammerId", scammer_id, incident_id, timestamp)

    if mule_account and phone_number:
        _merge_relationship(
            tx, "MuleAccount", mule_account, "PhoneNumber", phone_number,
            "USED_IN_CALL_WITH", incident_id, amount_requested, timestamp,
        )
    if phone_number and victim_region:
        _merge_relationship(
            tx, "PhoneNumber", phone_number, "VictimRegion", victim_region,
            "TARGETED_REGION", incident_id, None, timestamp,
        )
    if phone_number and scammer_id:
        _merge_relationship(
            tx, "PhoneNumber", phone_number, "ScammerId", scammer_id,
            "REQUESTED_PAYMENT_VIA", incident_id, amount_requested, timestamp,
        )


def push_incidents(driver: Driver, database: str, incidents: list[dict]) -> None:
    with driver.session(database=database) as session:
        for incident in incidents:
            session.execute_write(_push_incident, incident)


def push_single_incident(driver: Driver, database: str, incident: dict) -> None:
    """Same as push_incidents, for exactly one incident -- used by the
    auto-sync path so a single chat save doesn't need to reload/repush
    every incident in the database."""
    with driver.session(database=database) as session:
        session.execute_write(_push_incident, incident)
