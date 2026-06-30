"""Service layer for the geospatial intelligence API.

The backend wraps get_geospatial_data() in a FastAPI route -- that's the
only function it needs to call. Returns what's already in MongoDB
(geospatial_latest), which is kept current by the auto-sync after every
chat save, so this is always a fast read with no rebuild on request.

Suggested FastAPI route (paste into the backend's router):

    from src.graph.geospatial_service import get_geospatial_data

    @router.get("/geospatial")
    async def geospatial(heatmap: bool = False):
        return get_geospatial_data(include_heatmap=heatmap)

    # To serve the heatmap as a standalone HTML page:
    @router.get("/geospatial/heatmap", response_class=HTMLResponse)
    async def geospatial_heatmap():
        data = get_geospatial_data(include_heatmap=True)
        if data["heatmap_html"] is None:
            raise HTTPException(404, "No heatmap generated yet")
        return data["heatmap_html"]
"""

from __future__ import annotations

from src.graph.geospatial_store import load_latest_geospatial_snapshot


def get_geospatial_data(include_heatmap: bool = False) -> dict:
    """Returns the latest geospatial intelligence snapshot from MongoDB.

    Args:
        include_heatmap: if True, includes the full heatmap HTML string in
            the response (large -- omit for JSON API calls, include only
            when serving the HTML page directly).

    Returns a dict with:
        generated_at   -- ISO timestamp of when this snapshot was built
        hotspots       -- list of geocoded fraud hotspots, each with:
                          region, state, lat, lon, incident_count,
                          total_amount_demanded, total_amount_lost,
                          scam_types, risk_level ("high" / "normal")
        deployment_strategy -- top patrol deployment zones + methodology
        heatmap_html   -- full Folium HTML string (only if include_heatmap=True)
        available      -- False if no snapshot exists yet (no incidents saved)
    """
    snapshot = load_latest_geospatial_snapshot()
    if snapshot is None:
        return {"available": False, "hotspots": [], "deployment_strategy": {}, "heatmap_html": None, "generated_at": None}

    result = {
        "available": True,
        "generated_at": snapshot.get("generated_at"),
        "hotspots": snapshot.get("hotspots", []),
        "deployment_strategy": snapshot.get("deployment_strategy", {}),
        "heatmap_html": snapshot.get("heatmap_html") if include_heatmap else None,
    }
    return result
