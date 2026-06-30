"""Geocoded fraud hotspots per region. Geocoding via Nominatim with a local
JSON cache (one API hit per unique city)."""

import json
import time
from collections import defaultdict
from pathlib import Path

from server.graph.jurisdiction import map_region_to_jurisdiction

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "geocode_cache.json"

# A region at or above this incident count is flagged high-risk.
HOTSPOT_HIGH_RISK_THRESHOLD = 5

_geocode_cache: dict[str, tuple[float, float] | None] | None = None


def _load_cache() -> dict[str, tuple[float, float] | None]:
    global _geocode_cache
    if _geocode_cache is not None:
        return _geocode_cache
    if _CACHE_PATH.exists():
        raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        _geocode_cache = {
            k: tuple(v) if v is not None else None for k, v in raw.items()
        }
    else:
        _geocode_cache = {}
    return _geocode_cache


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _nominatim_lookup(query: str) -> tuple[float, float] | None:
    try:
        from geopy.geocoders import Nominatim

        geolocator = Nominatim(user_agent="cybersec-agent")
        location = geolocator.geocode(f"{query}, India", timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception:
        return None


def geocode_region(region: str | None) -> tuple[float, float] | None:
    if not region:
        return None
    key = region.strip().lower()
    cache = _load_cache()
    if key in cache:
        return cache[key]
    time.sleep(1)  # respect Nominatim's 1 req/s policy
    coords = _nominatim_lookup(key)
    cache[key] = coords
    _save_cache(cache)
    return coords


def _safe_float(value: float | int | str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_hotspots(incidents: list[dict]) -> tuple[list[dict], int]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    coords_map: dict[str, tuple[float, float]] = {}
    ungeocoded_count = 0

    for incident in incidents:
        region = incident.get("victim_region")
        if not region:
            continue
        coords = geocode_region(region)
        if coords is None:
            ungeocoded_count += 1
            continue
        key = region.strip().lower()
        buckets[key].append(incident)
        coords_map[key] = coords

    hotspots: list[dict] = []
    for region_key, members in buckets.items():
        lat, lon = coords_map[region_key]
        scam_types = sorted({m["scam_type"] for m in members if m.get("scam_type")})
        incident_count = len(members)
        hotspots.append(
            {
                "region": region_key.title(),
                "state": map_region_to_jurisdiction(region_key),
                "lat": lat,
                "lon": lon,
                "incident_count": incident_count,
                "total_amount_demanded": sum(
                    _safe_float(m.get("amount_demanded")) for m in members
                ),
                "total_amount_lost": sum(
                    _safe_float(m.get("amount_lost")) for m in members
                ),
                "scam_types": scam_types,
                "risk_level": "high"
                if incident_count >= HOTSPOT_HIGH_RISK_THRESHOLD
                else "normal",
            }
        )

    hotspots.sort(key=lambda h: h["incident_count"], reverse=True)
    return hotspots, ungeocoded_count


def build_geojson(hotspots: list[dict]) -> dict:
    """GeoJSON FeatureCollection -- coordinates are [lon, lat] per spec."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [h["lon"], h["lat"]]},
                "properties": {k: v for k, v in h.items() if k not in ("lat", "lon")},
            }
            for h in hotspots
        ],
    }
