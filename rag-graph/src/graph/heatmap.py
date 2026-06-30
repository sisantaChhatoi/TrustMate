"""Builds the command-centre interactive map: an NCRB cybercrime-density
baseline layer, with your own chat-collected fraud incidents overlaid as a
separate toggleable layer -- so a viewer can see "where cybercrime already
runs high nationally" versus "where our own incidents are concentrated"
side by side, not blended into one undifferentiated number.
"""

from __future__ import annotations

import folium
from folium.plugins import HeatMap

# Circle radius/heat-weight scaling -- purely visual, no statistical meaning.
_BASELINE_RADIUS_SCALE = 1.5
_OVERLAY_RADIUS_SCALE = 4.0


def build_heatmap(ncrb_baseline: list[dict], hotspots: list[dict]) -> folium.Map:
    if ncrb_baseline:
        center_lat = sum(c["lat"] for c in ncrb_baseline) / len(ncrb_baseline)
        center_lon = sum(c["lon"] for c in ncrb_baseline) / len(ncrb_baseline)
    else:
        center_lat, center_lon = 22.0, 79.0  # rough geographic centre of India

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="cartodbpositron")

    baseline_layer = folium.FeatureGroup(name="NCRB cybercrime baseline (2023)", show=True)
    HeatMap(
        [[c["lat"], c["lon"], c["cases_2023"]] for c in ncrb_baseline],
        name="NCRB density",
        radius=20,
        blur=15,
    ).add_to(baseline_layer)
    for city in ncrb_baseline:
        folium.CircleMarker(
            location=[city["lat"], city["lon"]],
            radius=max(3, city["crime_rate_2023"] * _BASELINE_RADIUS_SCALE),
            color="#4F46E5",
            fill=True,
            fill_opacity=0.4,
            popup=folium.Popup(
                f"<b>{city['city']}, {city['state']}</b><br>"
                f"2023 cases: {city['cases_2023']}<br>"
                f"Crime rate (per lakh): {city['crime_rate_2023']}<br>"
                f"Chargesheeting rate: {city['chargesheeting_rate_2023']}%",
                max_width=250,
            ),
        ).add_to(baseline_layer)
    baseline_layer.add_to(fmap)

    overlay_layer = folium.FeatureGroup(name="Our fraud incidents", show=True)
    for spot in hotspots:
        color = "#DC2626" if spot["risk_level"] == "high" else "#F59E0B"
        folium.CircleMarker(
            location=[spot["lat"], spot["lon"]],
            radius=max(5, spot["incident_count"] * _OVERLAY_RADIUS_SCALE),
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>{spot['region']}, {spot['state']}</b><br>"
                f"Our incidents: {spot['incident_count']}<br>"
                f"Scam types: {', '.join(spot['scam_types']) or 'unknown'}<br>"
                f"Demanded: Rs {spot['total_amount_demanded']:,.0f}<br>"
                f"Lost: Rs {spot['total_amount_lost']:,.0f}",
                max_width=250,
            ),
        ).add_to(overlay_layer)
    overlay_layer.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap
