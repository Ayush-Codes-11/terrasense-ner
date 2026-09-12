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
export type BasemapId = "street" | "terrain" | "satellite";
const BASEMAPS = {
  terrain: {
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    maxZoom: 17,
  },
  street: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EAP, and the GIS User Community',
    maxZoom: 19,
  },
} as const;
interface Props { data: Boundaries; focus: Boundaries; context?: Boundaries; level: "state" | "district" | "zone"; selected?: string; risks: RiskRecord[]; basemap: BasemapId; onSelect: (id: string) => void }
export default function HierarchyMap({ data, focus, context, level, selected, risks, basemap, onSelect }: Props) {
  const [tileErrorFor, setTileErrorFor] = useState<BasemapId>();
  const tileError = tileErrorFor === basemap;
  const riskMap = useMemo(() => new Map(risks.map(r => [r.zone_id, r])), [risks]);
  const idOf = (f?: Feature) => f?.properties?.[`${level}_id`] as string;
  const style = (f?: Feature) => ({ color: idOf(f) === selected ? "#ffffff" : level === "zone" ? "#3c454e" : "#227c8e", weight: idOf(f) === selected ? 3 : 1.5,
    fillColor: level === "zone" ? riskColors[riskMap.get(idOf(f))?.risk_category ?? ""] ?? "#8b98a6" : "#4da7b6", fillOpacity: level === "zone" ? 0.7 : 0.16 });
  const layerKey = JSON.stringify([level, data.features.map(f => idOf(f)), selected, risks.map(r => [r.zone_id, r.risk_category])]);
  return <div className="gis-map" aria-label="Interactive geographic map">
    <MapContainer center={[26, 93]} zoom={6} minZoom={4} maxZoom={18} scrollWheelZoom className="gis-leaflet">
      <TileLayer key={basemap} className={`gis-basemap gis-basemap-${basemap}`} url={BASEMAPS[basemap].url}
        attribution={BASEMAPS[basemap].attribution} maxZoom={BASEMAPS[basemap].maxZoom}
        eventHandlers={{ tileerror: () => setTileErrorFor(basemap) }} />
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
        const activate = () => onSelect(id);
        layer.on({ click: activate, mouseover: () => { if (layer instanceof L.Path) layer.setStyle({ weight: 3, fillOpacity: 0.45 }); },
          mouseout: () => { if (layer instanceof L.Path) layer.setStyle(style(feature)); } });
        if (layer instanceof L.Path) layer.on("add", () => {
          const element = layer.getElement();
          if (!element) return;
          element.setAttribute("role", "button");
          element.setAttribute("tabindex", "0");
          element.setAttribute("aria-label", level === "zone" ? `Zone ${name}` : name);
          element.addEventListener("keydown", event => {
            const key = (event as globalThis.KeyboardEvent).key;
            if (key === "Enter" || key === " ") { event.preventDefault(); activate(); }
          });
        });
      }} />
    </MapContainer>
    {tileError && <p className="gis-tile-notice" role="status">{BASEMAPS[basemap].attribution.includes("OpenStreetMap") ? "Basemap tiles unavailable. Boundary navigation remains available. OpenStreetMap attribution remains below." : "Basemap tiles unavailable. Boundary navigation remains available."}</p>}
  </div>;
}
