import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap, ScaleControl } from "react-leaflet";
import L from "leaflet";
import type { Feature } from "geojson";
import type { Boundaries, OperationalFeatureCollection, RiskRecord } from "../../services/spatial";
import { facilityCategory, facilityCategoryLabel, facilityColor } from "../../utils/operational";
import { riskColors, riskLabel } from "../../utils/navigation";
import { BASEMAPS } from "./mapConfig";
import type { BasemapId } from "./mapConfig";
import "leaflet/dist/leaflet.css";

export type { BasemapId } from "./mapConfig";

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
export interface HierarchyMapProps {
  data: Boundaries;
  focus: Boundaries;
  context?: Boundaries;
  level: "state" | "district" | "zone";
  selected?: string;
  risks: RiskRecord[];
  basemap: BasemapId;
  facilities?: OperationalFeatureCollection;
  roads?: OperationalFeatureCollection;
  showFacilities: boolean;
  showRoads: boolean;
  onSelect: (id: string) => void;
}
export default function HierarchyMap({ data, focus, context, level, selected, risks, basemap, facilities, roads, showFacilities, showRoads, onSelect }: HierarchyMapProps) {
  const [tileErrorFor, setTileErrorFor] = useState<BasemapId>();
  const tileError = tileErrorFor === basemap;
  const riskMap = useMemo(() => new Map(risks.map(r => [r.zone_id, r])), [risks]);
  const idOf = (f?: Feature) => f?.properties?.[`${level}_id`] as string;
  const style = (f?: Feature) => ({ color: idOf(f) === selected ? "#ffffff" : level === "zone" ? "#3c454e" : "#227c8e", weight: idOf(f) === selected ? 3 : 1.5,
    fillColor: level === "zone" ? riskColors[riskMap.get(idOf(f))?.risk_category ?? ""] ?? "#8b98a6" : "#4da7b6", fillOpacity: level === "zone" ? 0.7 : 0.16 });
  const layerKey = JSON.stringify([level, data.features.map(f => idOf(f)), selected, risks.map(r => [r.zone_id, r.risk_category])]);
  return <div className="gis-map" aria-label="Interactive geographic map">
    <MapContainer center={[26, 93]} zoom={6} minZoom={4} maxZoom={18} scrollWheelZoom className="gis-leaflet">
      <TileLayer key={basemap} className={`gis-basemap gis-basemap-${basemap}`} url={BASEMAPS[basemap].leafletUrl}
        attribution={BASEMAPS[basemap].attribution} maxZoom={BASEMAPS[basemap].maxZoom}
        eventHandlers={{ tileerror: () => setTileErrorFor(basemap) }} />
      <ScaleControl position="bottomleft" imperial={false} />
      <Viewport focus={focus} />
      {showRoads && roads && <GeoJSON key={`operational-roads-${roads.features.length}-${roads.data_meta.data_type}`} data={roads}
        interactive={false} style={feature => {
          const highway = String(feature?.properties?.highway ?? feature?.properties?.road_type ?? "");
          const major = ["motorway", "trunk", "primary", "secondary"].includes(highway);
          return { color: major ? "#d6a45f" : "#9aa8b5", weight: major ? 1.8 : 1.05, opacity: 0.48 };
        }} />}
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
      {showFacilities && facilities && <GeoJSON key={`operational-facilities-${facilities.features.length}-${facilities.data_meta.data_type}`} data={facilities}
        pointToLayer={(feature, latlng) => {
          const category = facilityCategory(feature.properties);
          return L.circleMarker(latlng, { radius: 5.5, color: "#f8fafc", weight: 1.5, fillColor: facilityColor(category), fillOpacity: 0.95 });
        }}
        onEachFeature={(feature, layer) => {
          const category = facilityCategory(feature.properties);
          const name = typeof feature.properties?.name === "string" && feature.properties.name.trim()
            ? feature.properties.name
            : `Unnamed ${category.replaceAll("_", " ")}`;
          const popup = document.createElement("div");
          popup.className = "gis-popup-content";
          const heading = document.createElement("h3");
          heading.className = "gis-popup-title";
          heading.textContent = name;
          const categoryLine = document.createElement("p");
          categoryLine.className = "gis-popup-meta";
          categoryLine.textContent = `Category: ${facilityCategoryLabel(category)}`;
          const sourceLine = document.createElement("p");
          sourceLine.className = "gis-popup-meta";
          sourceLine.textContent = `Source: ${String(feature.properties?.source ?? facilities.data_meta.source)}`;
          popup.append(heading, categoryLine, sourceLine);
          layer.bindPopup(popup, { className: "gis-popup" });
          if (layer instanceof L.Path) layer.on("add", () => {
            const element = layer.getElement();
            if (!element) return;
            element.setAttribute("role", "button");
            element.setAttribute("tabindex", "0");
            element.setAttribute("aria-label", `${name} · ${facilityCategoryLabel(category)}`);
            element.addEventListener("keydown", event => {
              const key = (event as globalThis.KeyboardEvent).key;
              if (key === "Enter" || key === " ") { event.preventDefault(); layer.openPopup(); }
            });
          });
        }} />}
    </MapContainer>
    {tileError && <p className="gis-tile-notice" role="status">{BASEMAPS[basemap].attribution.includes("OpenStreetMap") ? "Basemap tiles unavailable. Boundary navigation remains available. OpenStreetMap attribution remains below." : "Basemap tiles unavailable. Boundary navigation remains available."}</p>}
  </div>;
}
