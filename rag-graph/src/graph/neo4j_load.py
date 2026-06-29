"""Pushes incidents into Neo4j Aura as a property graph: MuleAccount,
PhoneNumber, VictimRegion, and ScammerId (the UPI handle a victim was asked
to pay) nodes, linked by USED_IN_CALL_WITH, TARGETED_REGION, and
REQUESTED_PAYMENT_VIA relationships. incident_count on nodes/relationships
is how reuse shows up -- the same account/number/UPI appearing across
multiple incidents increments it each time.

Call this against a freshly-cleared database (see neo4j_run.py) -- it's
MERGE-based so reruns without clearing would double-count, since there's no
way to tell "already pushed this incident" apart from "this is genuinely a
repeat occurrence" once the data's already in the graph.
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


def _push_incident(tx, incident: dict) -> None:
    incident_id = incident.get("incident_id") or str(incident.get("_id"))
    mule_account = _normalize(incident.get("mule_account"))
    phone_number = _normalize(incident.get("caller_number"))
    victim_region = _normalize(incident.get("victim_region"))
    scammer_id = _normalize(incident.get("mule_upi"))
    amount_requested = _safe_float(incident.get("amount_demanded"))
    timestamp = incident.get("timestamp")

    if mule_account:
        tx.run(
            """
            MERGE (a:MuleAccount {value: $value})
            ON CREATE SET a.incident_count = 1, a.first_seen = $timestamp, a.last_seen = $timestamp
            ON MATCH SET a.incident_count = a.incident_count + 1, a.last_seen = $timestamp
            """,
            value=mule_account,
            timestamp=timestamp,
        )

    if phone_number:
        tx.run(
            """
            MERGE (p:PhoneNumber {value: $value})
            ON CREATE SET p.incident_count = 1, p.first_seen = $timestamp, p.last_seen = $timestamp
            ON MATCH SET p.incident_count = p.incident_count + 1, p.last_seen = $timestamp
            """,
            value=phone_number,
            timestamp=timestamp,
        )

    if victim_region:
        tx.run(
            """
            MERGE (r:VictimRegion {value: $value})
            ON CREATE SET r.incident_count = 1, r.first_seen = $timestamp, r.last_seen = $timestamp
            ON MATCH SET r.incident_count = r.incident_count + 1, r.last_seen = $timestamp
            """,
            value=victim_region,
            timestamp=timestamp,
        )

    if scammer_id:
        tx.run(
            """
            MERGE (s:ScammerId {value: $value})
            ON CREATE SET s.incident_count = 1, s.first_seen = $timestamp, s.last_seen = $timestamp
            ON MATCH SET s.incident_count = s.incident_count + 1, s.last_seen = $timestamp
            """,
            value=scammer_id,
            timestamp=timestamp,
        )

    if mule_account and phone_number:
        tx.run(
            """
            MATCH (a:MuleAccount {value: $account}), (p:PhoneNumber {value: $phone})
            MERGE (a)-[rel:USED_IN_CALL_WITH]->(p)
            ON CREATE SET rel.incident_count = 1, rel.incident_ids = [$incident_id],
                          rel.amount_requested = $amount, rel.timestamp = $timestamp
            ON MATCH SET rel.incident_count = rel.incident_count + 1,
                         rel.incident_ids = rel.incident_ids + $incident_id
            """,
            account=mule_account,
            phone=phone_number,
            incident_id=incident_id,
            amount=amount_requested,
            timestamp=timestamp,
        )

    if phone_number and victim_region:
        tx.run(
            """
            MATCH (p:PhoneNumber {value: $phone}), (r:VictimRegion {value: $region})
            MERGE (p)-[rel:TARGETED_REGION]->(r)
            ON CREATE SET rel.incident_count = 1, rel.incident_ids = [$incident_id]
            ON MATCH SET rel.incident_count = rel.incident_count + 1,
                         rel.incident_ids = rel.incident_ids + $incident_id
            """,
            phone=phone_number,
            region=victim_region,
            incident_id=incident_id,
        )

    if phone_number and scammer_id:
        tx.run(
            """
            MATCH (p:PhoneNumber {value: $phone}), (s:ScammerId {value: $scammer_id})
            MERGE (p)-[rel:REQUESTED_PAYMENT_VIA]->(s)
            ON CREATE SET rel.incident_count = 1, rel.incident_ids = [$incident_id],
                          rel.amount_requested = $amount, rel.timestamp = $timestamp
            ON MATCH SET rel.incident_count = rel.incident_count + 1,
                         rel.incident_ids = rel.incident_ids + $incident_id
            """,
            phone=phone_number,
            scammer_id=scammer_id,
            incident_id=incident_id,
            amount=amount_requested,
            timestamp=timestamp,
        )


def push_incidents(driver: Driver, database: str, incidents: list[dict]) -> None:
    with driver.session(database=database) as session:
        for incident in incidents:
            session.execute_write(_push_incident, incident)
