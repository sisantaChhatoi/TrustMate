"""Builds geocoded fraud hotspots, the NCRB-baseline heatmap, and the
patrol deployment ranking from MongoDB incidents.

Usage:
    python -m src.graph.geospatial_run

Note: this same build also runs automatically after every chat save (see
incident_store.py's auto-sync) -- this command is for an on-demand rerun
or to get the human-readable summary.txt, not the only way it updates.
"""

from __future__ import annotations

from pathlib import Path

from src.graph.geospatial import HOTSPOT_HIGH_RISK_THRESHOLD
from src.graph.geospatial_pipeline import OUTPUT_DIR, regenerate_geospatial_outputs


def _write_summary(path: Path, hotspots: list[dict], ungeocoded_count: int, total_incidents: int) -> None:
    lines = [
        "GEOSPATIAL CRIME PATTERN SUMMARY",
        "=" * 50,
        f"Incidents analyzed: {total_incidents}",
        f"Geocoded into {len(hotspots)} region(s); {ungeocoded_count} incident(s) had an unrecognized "
        "or missing victim_region and couldn't be placed on the map.",
        "",
        f"HIGH-RISK REGIONS ({HOTSPOT_HIGH_RISK_THRESHOLD}+ incidents -- prioritise patrol attention)",
        "-" * 50,
    ]
    high_risk = [h for h in hotspots if h["risk_level"] == "high"]
    if high_risk:
        for h in high_risk:
            lines.append(
                f"  {h['region']}, {h['state']} -- {h['incident_count']} incidents, "
                f"scam types: {', '.join(h['scam_types']) or 'unknown'}"
            )
    else:
        lines.append("  None yet -- needs more data for a region to cross the threshold.")
    lines.append("")

    lines.append("ALL REGIONS BY INCIDENT COUNT")
    lines.append("-" * 50)
    for h in hotspots:
        lines.append(
            f"  {h['region']}, {h['state']} -- {h['incident_count']} incident(s) "
            f"-- Rs {h['total_amount_demanded']:,.0f} demanded, Rs {h['total_amount_lost']:,.0f} lost"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    result = regenerate_geospatial_outputs()
    print(f"Loaded {len(result['incidents'])} incidents from MongoDB.")
    print(f"Geocoded {len(result['hotspots'])} region(s); {result['ungeocoded_count']} incident(s) ungeocoded.")
    print(f"Loaded NCRB baseline: {len(result['ncrb_baseline'])} cities.")

    _write_summary(
        OUTPUT_DIR / "geospatial_summary.txt", result["hotspots"], result["ungeocoded_count"], len(result["incidents"])
    )

    print(f"\nOutputs written to {OUTPUT_DIR}, and synced to Mongo (geospatial_latest):")
    print("  - geospatial_hotspots.json")
    print("  - geospatial_hotspots.geojson")
    print("  - geospatial_summary.txt")
    print("  - geospatial_heatmap.html")
    print("  - deployment_strategy.json")


if __name__ == "__main__":
    main()
