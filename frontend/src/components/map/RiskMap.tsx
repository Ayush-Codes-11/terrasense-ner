// ============================================================
// RiskMap — Leaflet map centered on Aizawl, Mizoram
// Phase 2: renders sample GeoJSON risk grid + OSM tile base
// Phase 5+: real OSM roads/villages and SRTM-derived zones
//
// Replaces MapPlaceholder. Do not import MapPlaceholder here.
// ============================================================

import { useCallback, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Polyline,
  Popup,
  LayersControl,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { Feature, Geometry, GeoJsonObject } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";

import type { GeoJSONData } from "../../hooks/useGeoJSONData";
import type {
  ZoneGeoJSONProperties,
  RoadGeoJSONProperties,
  VillageGeoJSONProperties,
  FacilityGeoJSONProperties,
} from "../../types/geojson";
import { RISK_COLORS } from "../../utils/risk";

// ---- Aizawl pilot area constants ----
const AIZAWL_CENTER: [number, number] = [23.7271, 92.7176];
const DEFAULT_ZOOM = 13;

// ---- Risk colour helpers ----

function riskColor(category: string): string {
  const map: Record<string, string> = {
    LOW: RISK_COLORS.LOW,
    MODERATE: RISK_COLORS.MODERATE,
    HIGH: RISK_COLORS.HIGH,
    VERY_HIGH: RISK_COLORS.VERY_HIGH,
  };
  return map[category] ?? "#94a3b8";
}

// ---- Custom map legend control ----

function MapLegend() {
  const map = useMap();
  useEffect(() => {
    const legend = new L.Control({ position: "bottomleft" });
    legend.onAdd = () => {
      const div = L.DomUtil.create("div");
      div.style.cssText =
        "background:rgba(15,23,42,0.92);border:1px solid rgba(71,85,105,0.6);border-radius:6px;padding:8px 10px;font-size:11px;color:#cbd5e1;min-width:120px;";
      const items: [string, string][] = [
        ["LOW", "#22c55e"],
        ["MODERATE", "#eab308"],
        ["HIGH", "#f97316"],
        ["VERY HIGH", "#ef4444"],
      ];
      div.innerHTML =
        `<div style="font-weight:600;font-size:10px;letter-spacing:0.05em;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;">Risk Level</div>` +
        items
          .map(
            ([label, color]) =>
              `<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
                <div style="width:12px;height:12px;border-radius:2px;background:${color};opacity:0.85;flex-shrink:0;"></div>
                <span>${label}</span>
              </div>`
          )
          .join("") +
        `<div style="border-top:1px solid rgba(71,85,105,0.4);margin-top:6px;padding-top:5px;font-size:9px;color:#475569;">
          <span style="background:rgba(251,191,36,0.2);border:1px solid rgba(251,191,36,0.4);color:#fbbf24;border-radius:3px;padding:1px 4px;">SAMPLE</span>
          &nbsp;Not geospatially accurate
        </div>`;
      return div;
    };
    legend.addTo(map);
    return () => {
      legend.remove();
    };
  }, [map]);
  return null;
}

// ---- Road colour by type ----

function roadColor(type: string): string {
  const map: Record<string, string> = {
    national_highway: "#60a5fa",
    state_highway: "#818cf8",
    district_road: "#a78bfa",
    local_road: "#94a3b8",
  };
  return map[type] ?? "#94a3b8";
}

function roadWeight(type: string): number {
  return type === "national_highway" ? 3 : type === "state_highway" ? 2.5 : 2;
}

// ---- Props ----

interface RiskMapProps {
  geoData: GeoJSONData;
  selectedZoneId: string | null;
  onZoneSelect: (props: ZoneGeoJSONProperties) => void;
}

// ---- Main component ----

export default function RiskMap({
  geoData,
  selectedZoneId,
  onZoneSelect,
}: RiskMapProps) {
  const { gridRisk, roads, villages, hospitals, loading, error } = geoData;

  // Style function for risk zones — key changes on selection to force re-render
  const riskStyle = useCallback(
    (feature?: Feature<Geometry, ZoneGeoJSONProperties>): PathOptions => {
      const cat = feature?.properties?.risk_category ?? "LOW";
      const isSelected =
        feature?.properties?.zone_id === selectedZoneId;
      return {
        fillColor: riskColor(cat),
        fillOpacity: isSelected ? 0.65 : 0.35,
        color: isSelected ? "#ffffff" : riskColor(cat),
        weight: isSelected ? 2.5 : 1.2,
        opacity: 0.9,
      };
    },
    [selectedZoneId]
  );

  // Bind click + hover to each zone polygon
  const onEachZone = useCallback(
    (feature: Feature, layer: Layer) => {
      const props = feature.properties as ZoneGeoJSONProperties;
      layer.on({
        click: () => onZoneSelect(props),
        mouseover: (e) => {
          (e.target as L.Path).setStyle({ fillOpacity: 0.6, weight: 2 });
        },
        mouseout: (e) => {
          const isSelected = props.zone_id === selectedZoneId;
          (e.target as L.Path).setStyle({
            fillOpacity: isSelected ? 0.65 : 0.35,
            weight: isSelected ? 2.5 : 1.2,
          });
        },
      });
    },
    [selectedZoneId, onZoneSelect]
  );

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden border border-slate-700">
      {/* Sample data banner */}
      <div className="absolute top-2 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 border border-amber-500/40 text-[10px] text-amber-400 font-medium pointer-events-none">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        Sample data · not geospatially accurate · Aizawl pilot area
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 z-[999] flex items-center justify-center bg-slate-950/80 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <svg
              className="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8z"
              />
            </svg>
            Loading map layers…
          </div>
        </div>
      )}

      {/* Error overlay */}
      {error && (
        <div className="absolute inset-0 z-[999] flex items-center justify-center bg-slate-950/80 rounded-lg">
          <div className="text-center text-sm text-red-400 p-4">
            <p className="font-semibold">Failed to load GeoJSON</p>
            <p className="text-xs text-slate-500 mt-1">{error}</p>
          </div>
        </div>
      )}

      <MapContainer
        center={AIZAWL_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%", background: "#0f172a" }}
        zoomControl={true}
      >
        {/* CartoDB Dark tile layer — good contrast with risk colours */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
          maxZoom={19}
          subdomains="abcd"
        />

        {/* Custom legend */}
        <MapLegend />

        <LayersControl position="topright">
          {/* ── Risk Zones ── */}
          <LayersControl.Overlay checked name="⬛ Risk Zones (sample)">
            {gridRisk && (
              <GeoJSON
                key={`risk-${selectedZoneId ?? "none"}`}
                data={gridRisk as GeoJsonObject}
                style={
                  riskStyle as (
                    feature?: Feature<Geometry>
                  ) => PathOptions
                }
                onEachFeature={onEachZone}
              />
            )}
          </LayersControl.Overlay>

          {/* ── Roads ── */}
          <LayersControl.Overlay checked name="🛣 Roads (sample)">
            <>
              {roads?.features.map((f, i) => {
                const props = f.properties as RoadGeoJSONProperties;
                const coords = (
                  f.geometry as GeoJSON.LineString
                ).coordinates.map(([lon, lat]) => [lat, lon] as [number, number]);
                return (
                  <Polyline
                    key={props.road_id ?? i}
                    positions={coords}
                    pathOptions={{
                      color: roadColor(props.road_type),
                      weight: roadWeight(props.road_type),
                      opacity: 0.8,
                      dashArray:
                        props.road_type === "local_road" ? "4 4" : undefined,
                    }}
                  >
                    <Popup>
                      <div className="text-xs">
                        <p className="font-semibold">{props.name}</p>
                        <p className="text-slate-500 capitalize">
                          {props.road_type.replace(/_/g, " ")}
                        </p>
                        <p className="text-amber-500 text-[10px] mt-1">
                          SAMPLE MOCK
                        </p>
                      </div>
                    </Popup>
                  </Polyline>
                );
              })}
            </>
          </LayersControl.Overlay>

          {/* ── Villages ── */}
          <LayersControl.Overlay checked name="🏘 Villages (sample)">
            <>
              {villages?.features.map((f, i) => {
                const props = f.properties as VillageGeoJSONProperties;
                const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
                return (
                  <CircleMarker
                    key={props.village_id ?? i}
                    center={[lat, lon]}
                    radius={5}
                    pathOptions={{
                      color: "#60a5fa",
                      fillColor: "#60a5fa",
                      fillOpacity: 0.8,
                      weight: 1.5,
                    }}
                  >
                    <Popup>
                      <div className="text-xs">
                        <p className="font-semibold">{props.name}</p>
                        <p className="text-slate-500">
                          Pop. est. {props.population_est.toLocaleString()}
                        </p>
                        <p className="text-slate-500">
                          Zone: {props.zone_id}
                        </p>
                        <p className="text-amber-500 text-[10px] mt-1">
                          SAMPLE MOCK
                        </p>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </>
          </LayersControl.Overlay>

          {/* ── Critical Facilities ── */}
          <LayersControl.Overlay checked name="🏥 Critical Facilities (sample)">
            <>
              {hospitals?.features.map((f, i) => {
                const props = f.properties as FacilityGeoJSONProperties;
                const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
                return (
                  <CircleMarker
                    key={props.facility_id ?? i}
                    center={[lat, lon]}
                    radius={6}
                    pathOptions={{
                      color: "#f87171",
                      fillColor: "#ef4444",
                      fillOpacity: 0.85,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="text-xs">
                        <p className="font-semibold">{props.name}</p>
                        <p className="text-slate-500 capitalize">
                          {props.facility_type.replace(/_/g, " ")}
                        </p>
                        <p className="text-slate-500">Zone: {props.zone_id}</p>
                        <p className="text-amber-500 text-[10px] mt-1">
                          SAMPLE MOCK
                        </p>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </>
          </LayersControl.Overlay>
        </LayersControl>
      </MapContainer>
    </div>
  );
}
