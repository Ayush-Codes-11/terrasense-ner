import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap, ScaleControl } from "react-leaflet";
import L from "leaflet";
import type { Feature } from "geojson";
import type { Boundaries, RiskRecord } from "../../services/spatial";
import { riskColors, riskLabel } from "../../utils/navigation";
import "leaflet/dist/leaflet.css";

function Viewport({ focus }: { focus: Boundaries }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.geoJSON(focus).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14, animate: false });
  }, [map, focus]);
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}
interface Props { data: Boundaries; focus: Boundaries; context?: Boundaries; level: "state" | "district" | "zone"; selected?: string; risks: RiskRecord[]; onSelect: (id: string) => void }
export default function HierarchyMap({ data, focus, context, level, selected, risks, onSelect }: Props) {
  const [tileError, setTileError] = useState(false);
  const riskMap = useMemo(() => new Map(risks.map(r => [r.zone_id, r])), [risks]);
  const idOf = (f?: Feature) => f?.properties?.[`${level}_id`] as string;
  const style = (f?: Feature) => ({ color: idOf(f) === selected ? "#ffffff" : level === "zone" ? "#3c454e" : "#227c8e", weight: idOf(f) === selected ? 3 : 1.5,
    fillColor: level === "zone" ? riskColors[riskMap.get(idOf(f))?.risk_category ?? ""] ?? "#8b98a6" : "#4da7b6", fillOpacity: level === "zone" ? 0.7 : 0.16 });
  const layerKey = JSON.stringify([level, data.features.map(f => idOf(f)), selected, risks.map(r => [r.zone_id, r.risk_category])]);
  return <div className="gis-map" aria-label="Interactive geographic map">
    <MapContainer center={[26, 93]} zoom={6} minZoom={4} maxZoom={18} scrollWheelZoom className="gis-leaflet">
      <TileLayer className="gis-basemap" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        eventHandlers={{ tileerror: () => setTileError(true) }} />
      <ScaleControl position="bottomleft" imperial={false} />
      <Viewport focus={focus} />
      {context && <GeoJSON key={JSON.stringify(context.features.map(f => f.properties.district_id))} data={context} interactive={false}
        style={{ color: "#64717b", weight: 2, fillOpacity: 0, dashArray: "5 5" }} />}
      <GeoJSON key={layerKey} data={data} style={style} onEachFeature={(feature, layer) => {
        const id = idOf(feature);
        const name = feature.properties?.[`${level}_name`] ?? id;
        const label = document.createElement("span");
        label.textContent = level === "zone" ? `${name} · ${riskLabel(riskMap.get(id)?.risk_category)}` : name;
        layer.bindTooltip(label, { sticky: true });
        layer.on({ click: () => onSelect(id), mouseover: () => { if (layer instanceof L.Path) layer.setStyle({ weight: 3, fillOpacity: 0.45 }); },
          mouseout: () => { if (layer instanceof L.Path) layer.setStyle(style(feature)); } });
      }} />
    </MapContainer>
    {tileError && <p className="gis-tile-notice" role="status">Basemap tiles unavailable. Boundary navigation remains available.</p>}
  </div>;
}
