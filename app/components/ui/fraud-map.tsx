import { View } from 'react-native';
import WebView from 'react-native-webview';

import { colors, radius } from '@/constants/design';
import type { FraudHotspot } from '@/lib/api';

const RISK_HEX: Record<string, string> = {
  high: '#DC2626',
  medium: '#D97706',
  low: '#059669',
};

function buildMapHtml(hotspots: FraudHotspot[]): string {
  const markers = hotspots
    .filter((h) => h.lat && h.lon)
    .map((h) => {
      const color = RISK_HEX[h.risk_level] ?? '#06B6D4';
      const r = h.incident_count > 5 ? 18 : h.incident_count > 2 ? 12 : 8;
      const popup = `<b>${h.region}</b><br/>${h.state}<br/>${h.incident_count} report${h.incident_count !== 1 ? 's' : ''}${h.total_amount_lost > 0 ? '<br/>₹' + (h.total_amount_lost / 1000).toFixed(0) + 'K lost' : ''}`;
      return `L.circleMarker([${h.lat},${h.lon}],{radius:${r},color:'${color}',fillColor:'${color}',fillOpacity:0.7,weight:2}).bindPopup(\`${popup}\`).addTo(map);`;
    })
    .join('\n');

  return `<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>*{margin:0;padding:0;box-sizing:border-box}html,body,#map{width:100%;height:100%}</style>
</head><body><div id="map"></div>
<script>
const map=L.map('map',{zoomControl:true}).setView([22.5,80.0],4);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(map);
${markers}
</script></body></html>`;
}

export function FraudMap({ hotspots }: { hotspots: FraudHotspot[] }) {
  const mapped = hotspots.filter((h) => h.lat && h.lon);
  if (mapped.length === 0) return null;

  return (
    <View
      style={{
        height: 280,
        borderRadius: radius.xl,
        overflow: 'hidden',
        backgroundColor: colors.card,
      }}>
      <WebView
        source={{ html: buildMapHtml(hotspots) }}
        style={{ flex: 1 }}
        scrollEnabled={false}
        javaScriptEnabled
      />
    </View>
  );
}
