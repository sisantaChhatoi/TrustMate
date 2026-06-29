"""Writes a human-readable summary report of the fraud network analysis."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from src.graph.analyze import HIGH_RISK_INCIDENT_THRESHOLD


def write_summary_report(
    path: Path, graph: nx.Graph, rings: list[dict], intelligence: dict[str, dict], total_incidents: int
) -> None:
    lines = [
        "FRAUD NETWORK INTELLIGENCE SUMMARY",
        "=" * 50,
        f"Incidents analyzed: {total_incidents}",
        f"Graph nodes: {graph.number_of_nodes()}  |  edges: {graph.number_of_edges()}",
        f"Fraud rings detected (2+ linked entities): {len(rings)}",
        "",
        f"HIGH-RISK ENTITIES (appear in {HIGH_RISK_INCIDENT_THRESHOLD}+ incidents -- coordinated operation signal)",
        "-" * 50,
    ]

    high_risk = sorted(
        (v for v in intelligence.values() if v["risk_level"] == "high"),
        key=lambda v: v["incident_count"],
        reverse=True,
    )
    if high_risk:
        for entry in high_risk:
            lines.append(f"  [{entry['type']}] {entry['value']} -- {entry['incident_count']} incidents")
    else:
        lines.append("  None yet -- needs more data for coordinated reuse to surface.")
    lines.append("")

    lines.append("TOP FRAUD RINGS BY INCIDENT COUNT")
    lines.append("-" * 50)
    if not rings:
        lines.append("  None yet -- no entity has co-occurred with another across incidents.")
    for ring in rings[:10]:
        lines.append(
            f"  Ring #{ring['ring_id']} -- {ring['incident_count']} incident(s), "
            f"{ring['size']} linked entities, scam types: {', '.join(ring['scam_types']) or 'unknown'}"
        )
        if ring["mule_accounts"]:
            lines.append(f"    Mule accounts: {', '.join(ring['mule_accounts'])}")
        if ring["phone_numbers"]:
            lines.append(f"    Phone numbers: {', '.join(ring['phone_numbers'])}")
        if ring["victim_regions"]:
            lines.append(f"    Victim regions: {', '.join(ring['victim_regions'])}")
        if ring["scammer_ids"]:
            lines.append(f"    Scammer UPI IDs: {', '.join(ring['scammer_ids'])}")
        lines.append(
            f"    Total demanded: Rs {ring['total_amount_demanded']:,.0f}  |  "
            f"Total lost: Rs {ring['total_amount_lost']:,.0f}"
        )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
