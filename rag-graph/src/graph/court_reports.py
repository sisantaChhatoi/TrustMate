"""Builds and writes the requested output content: a combined JSON, one
evidence package per ring, a cross-jurisdiction alert, and an overall
summary.

Each "build_*" function returns plain content (str/dict/list) and has no
side effects -- the "write_*" functions just write that same content to
disk. This split exists so evidence_store.py can persist the EXACT same
report text/data to MongoDB instead of only ever existing as local files.

DISCLAIMER baked into every text report: this is automated investigative
support generated from chat-collected incident reports, not a substitute
for formal evidentiary procedure (chain of custody, victim statements,
forensic verification). It's meant to help an investigator triage and
prioritize, not to stand on its own in court.
"""

from __future__ import annotations

import json
from pathlib import Path

DISCLAIMER = (
    "DISCLAIMER: This report is system-generated investigative intelligence,\n"
    "derived automatically from chat-collected incident reports. It is meant\n"
    "to help an investigator triage and prioritize leads -- it is NOT a\n"
    "substitute for formal evidentiary procedure (chain of custody, victim\n"
    "statements, forensic verification) and should be independently verified\n"
    "before any legal action is taken on it.\n"
)


def build_evidence_report_text(ring: dict) -> str:
    ring_id = ring["fraud_ring_id"]
    lines = [
        DISCLAIMER,
        f"DETAILED EVIDENCE REPORT -- {ring_id}",
        "=" * 60,
        f"Ring type: {ring['ring_type']}",
        f"Confidence score: {ring['confidence_score']['score']} (method: {ring['confidence_score']['method']})",
        f"Victims reached (distinct incidents): {ring['total_victims_reached']}",
        f"Total amount requested: {ring['total_amount_requested_formatted']} (Rs {ring['total_amount_requested']:,.0f})",
        f"Total amount lost: {ring['total_amount_lost_formatted']} (Rs {ring['total_amount_lost']:,.0f})",
        f"Jurisdictions affected: {', '.join(ring['jurisdictions_affected']) or 'Unknown'}",
        f"Operation timeframe: {ring['operation_timeframe']['start']} to {ring['operation_timeframe']['end']}",
        "",
        "CORE MEMBERS",
        "-" * 60,
    ]
    for member in ring["core_members"]:
        lines.append("  " + ", ".join(f"{k}: {v}" for k, v in member.items()))
    lines.append("")

    lines.append("CHRONOLOGICAL INCIDENT LINKING (evidence chain)")
    lines.append("-" * 60)
    for entry in ring["evidence_chain"]:
        lines.append(
            f"  [{entry['incident_timestamp']}] incident {entry['incident_id']} "
            f"(victim ref: {entry['victim_session_ref']}, region: {entry['region']}, status: {entry['status']})"
        )
        lines.append(
            f"      phone: {entry['phone_used']}  |  mule account: {entry['mule_account_used']}  |  "
            f"UPI: {entry['scammer_upi_used']}"
        )
        lines.append(f"      amount requested: {entry['amount_requested']}  |  amount lost: {entry['amount_lost']}")
    lines.append("")

    return "\n".join(lines)


def build_network_diagram(ring: dict) -> dict:
    return {
        "fraud_ring_id": ring["fraud_ring_id"],
        "mule_account_network": ring["mule_account_network"],
        "phone_call_network": ring["phone_call_network"],
    }


def build_jurisdiction_summary(ring: dict) -> dict:
    return {
        "fraud_ring_id": ring["fraud_ring_id"],
        "jurisdictions_affected": ring["jurisdictions_affected"],
        "victim_regions": ring["victim_regions"],
        "recommended_agencies": [f"Cyber Cell -- {j}" for j in ring["jurisdictions_affected"] if j != "Unknown"],
    }


def build_inter_jurisdiction_alert(rings: list[dict]) -> list[dict]:
    return [
        {
            "fraud_ring_id": r["fraud_ring_id"],
            "jurisdictions_affected": r["jurisdictions_affected"],
            "total_victims_reached": r["total_victims_reached"],
            "total_amount_requested": r["total_amount_requested"],
        }
        for r in rings
        if len(r["jurisdictions_affected"]) > 1
    ]


def build_summary_statistics_text(rings: list[dict], total_incidents: int) -> str:
    total_requested = sum(r["total_amount_requested"] for r in rings)
    total_lost = sum(r["total_amount_lost"] for r in rings)
    multi_state = [r for r in rings if len(r["jurisdictions_affected"]) > 1]
    core_operators = [
        m["mule_account"] for r in rings for m in r["core_members"] if "mule_account" in m and m.get("is_core_operator")
    ]

    lines = [
        DISCLAIMER,
        "SUMMARY STATISTICS",
        "=" * 60,
        f"Incidents analyzed: {total_incidents}",
        f"Fraud rings detected: {len(rings)}",
        f"Rings spanning multiple states: {len(multi_state)}",
        f"Core operator accounts (5+ incidents): {len(core_operators)}",
        f"Total amount requested across all rings: Rs {total_requested:,.0f}",
        f"Total amount lost across all rings: Rs {total_lost:,.0f}",
        "",
        "RINGS BY VICTIMS REACHED",
        "-" * 60,
    ]
    for r in rings:
        lines.append(
            f"  {r['fraud_ring_id']} ({r['ring_type']}) -- {r['total_victims_reached']} victims, "
            f"confidence {r['confidence_score']['score']}, jurisdictions: {', '.join(r['jurisdictions_affected']) or 'Unknown'}"
        )

    return "\n".join(lines)


def write_fraud_rings_complete(path: Path, rings: list[dict]) -> None:
    path.write_text(json.dumps(rings, indent=2, ensure_ascii=False), encoding="utf-8")


def write_evidence_package(folder: Path, ring: dict) -> None:
    """One JSON + one human-readable .txt per ring, inside folder."""
    folder.mkdir(parents=True, exist_ok=True)
    ring_id = ring["fraud_ring_id"]

    (folder / f"{ring_id}.json").write_text(json.dumps(ring, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / f"{ring_id}_detailed_evidence_report.txt").write_text(
        build_evidence_report_text(ring), encoding="utf-8"
    )
    (folder / f"{ring_id}_network_diagram.json").write_text(
        json.dumps(build_network_diagram(ring), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (folder / f"{ring_id}_jurisdiction_summary.json").write_text(
        json.dumps(build_jurisdiction_summary(ring), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def write_inter_jurisdiction_alert(path: Path, rings: list[dict]) -> None:
    path.write_text(json.dumps(build_inter_jurisdiction_alert(rings), indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary_statistics(path: Path, rings: list[dict], total_incidents: int) -> None:
    path.write_text(build_summary_statistics_text(rings, total_incidents), encoding="utf-8")
