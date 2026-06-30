"""Shared core of the geospatial intelligence build -- used by both the
manual CLI (geospatial_run.py) and the auto-sync triggered after every chat
save (incident_store.py), so there's exactly one place that defines what
"regenerate the geospatial outputs" means.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.graph.data import load_incidents
from src.graph.deployment import build_deployment_strategy
from src.graph.geospatial import build_geojson, build_hotspots
from src.graph.geospatial_store import save_geospatial_snapshot
from src.graph.heatmap import build_heatmap
from src.graph.ncrb_baseline import load_ncrb_baseline

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "graph"


def regenerate_geospatial_outputs() -> dict:
    """Rebuilds hotspots, the deployment ranking, and the heatmap from
    whatever's currently in MongoDB; writes the local files in
    data/graph/ and persists the same content to Mongo (see
    geospatial_store.py). Returns the raw materials (hotspots,
    ungeocoded_count, ncrb_baseline, deployment_strategy) so a caller that
    wants the human-readable summary.txt (only geospatial_run.py does)
    doesn't have to redo the work."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    incidents = load_incidents()
    hotspots, ungeocoded_count = build_hotspots(incidents)
    ncrb_baseline = load_ncrb_baseline()
    deployment_strategy = build_deployment_strategy(ncrb_baseline, hotspots)
    fmap = build_heatmap(ncrb_baseline, hotspots)
    heatmap_html = fmap.get_root().render()

    (OUTPUT_DIR / "geospatial_hotspots.json").write_text(
        json.dumps(hotspots, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_DIR / "geospatial_hotspots.geojson").write_text(
        json.dumps(build_geojson(hotspots), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUTPUT_DIR / "geospatial_heatmap.html").write_text(heatmap_html, encoding="utf-8")
    (OUTPUT_DIR / "deployment_strategy.json").write_text(
        json.dumps(deployment_strategy, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    save_geospatial_snapshot(hotspots, deployment_strategy, heatmap_html)

    return {
        "incidents": incidents,
        "hotspots": hotspots,
        "ungeocoded_count": ungeocoded_count,
        "ncrb_baseline": ncrb_baseline,
        "deployment_strategy": deployment_strategy,
    }
