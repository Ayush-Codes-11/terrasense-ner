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

function MapResizeFix() {
  const map = useMap();
  useEffect(() => {
    requestAnimationFrame(() => {
      map.invalidateSize();
    });
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 200);
    return () => clearTimeout(timer);
  }, [map]);
  return null;
}

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
        "background:rgba(16,31,53,0.90);backdrop-filter:blur(8px);border:1px solid rgba(148,163,184,0.15);border-radius:8px;padding:10px 12px;font-size:11px;color:#cbd5e1;box-shadow:0 8px 24px rgba(0,0,0,0.4);";
      const items: [string, string][] = [
        ["LOW", RISK_COLORS.LOW],
        ["MODERATE", RISK_COLORS.MODERATE],
        ["HIGH", RISK_COLORS.HIGH],
        ["VERY HIGH", RISK_COLORS.VERY_HIGH],
      ];
      div.innerHTML =
        `<div style="font-weight:700;font-size:10px;letter-spacing:0.05em;color:#94a3b8;margin-bottom:8px;text-transform:uppercase;">Risk Level</div>` +
        items
          .map(
            ([label, color]) =>
              `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                <div style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0;box-shadow:0 0 4px ${color}80;"></div>
                <span style="font-weight:500;">${label}</span>
              </div>`
          )
          .join("");
      return div;
    };
    legend.addTo(map);
    return () => {
      legend.remove();
    };
  }, [map]);
  return null;
}

// ---- Road colour by type / OSM highway ----

function roadColor(type?: string): string {
  if (!type) return "#94a3b8";
  const map: Record<string, string> = {
    national_highway: "#60a5fa",
    motorway: "#60a5fa",
    trunk: "#60a5fa",
    primary: "#60a5fa",
    state_highway: "#818cf8",
    secondary: "#818cf8",
    district_road: "#a78bfa",
    tertiary: "#a78bfa",
    unclassified: "#94a3b8",
    residential: "#94a3b8",
    living_street: "#94a3b8",
    service: "#64748b",
    track: "#78716c",
    path: "#64748b",
    footway: "#64748b",
    local_road: "#94a3b8",
  };
  return map[type] ?? "#94a3b8";
}

function roadWeight(type?: string): number {
  if (!type) return 1.5;
  if (["national_highway", "motorway", "trunk", "primary"].includes(type)) return 3;
  if (["state_highway", "secondary"].includes(type)) return 2.5;
  if (["district_road", "tertiary"].includes(type)) return 2;
  return 1.5;
}

import type { Zone } from "../../types";

// ---- Props ----

interface RiskMapProps {
  geoData: GeoJSONData;
  selectedZoneId: string | null;
  onZoneSelect: (props: ZoneGeoJSONProperties) => void;
  zoneRisks?: Map<string, Zone> | null;
  isRiskFallback?: boolean;
  /** True when API is reachable but returning SAMPLE/fixture data (not real observations) */
  isDataSample?: boolean;
  reports?: any[];
  className?: string;
}

// ---- Main component ----

export default function RiskMap({
  geoData,
  selectedZoneId,
  onZoneSelect,
  zoneRisks,
  isRiskFallback = false,
  isDataSample = true,
  reports = [],
  className = "",
}: RiskMapProps) {
  const { gridRisk, roads, villages, hospitals, loading, error } = geoData;

  // Style function for risk zones — uses API computed risk if available, else sample GeoJSON
  const riskStyle = useCallback(
    (feature?: Feature<Geometry, ZoneGeoJSONProperties>): PathOptions => {
      const zoneId = feature?.properties?.zone_id;
      const computedZone = zoneId ? zoneRisks?.get(zoneId) : undefined;
      const cat = computedZone?.risk ?? feature?.properties?.risk_category ?? "LOW";
      const isSelected = feature?.properties?.zone_id === selectedZoneId;
      return {
        fillColor: riskColor(cat),
        fillOpacity: isSelected ? 0.45 : 0.35,
        color: isSelected ? "#22D3EE" : riskColor(cat),
        weight: isSelected ? 2.5 : 0.5,
        opacity: isSelected ? 1 : 0.4,
      };
    },
    [selectedZoneId, zoneRisks]
  );

  // Bind click + hover to each zone polygon
  const onEachZone = useCallback(
    (feature: Feature, layer: Layer) => {
      const props = feature.properties as ZoneGeoJSONProperties;
      const computedZone = zoneRisks?.get(props.zone_id);
      const scoreStr =
        computedZone?.score !== undefined
          ? computedZone.score.toFixed(4)
          : props.risk_score.toFixed(2);
      const cat = computedZone?.risk ?? props.risk_category;
      const catLabel = cat.replace("_", " ");

      layer.bindPopup(
        `<div style="font-size:11px;line-height:1.4;color:#0f172a;min-width:120px;">
          <div style="font-weight:700;font-size:12px;margin-bottom:2px;">Zone ${props.zone_id}</div>
          <div>Risk Level: <strong>${catLabel}</strong></div>
          <div>Prototype Score: <strong>${scoreStr}</strong></div>
          <div style="font-size:9px;color:#64748b;margin-top:4px;border-top:1px solid #e2e8f0;padding-top:2px;">
            ${isRiskFallback ? "SAMPLE_MOCK fallback" : "Computed via Prototype Scorer"}<br/>
            Georeferenced prototype analysis boundary
          </div>
        </div>`
      );

      layer.on({
        click: () => onZoneSelect(props),
        mouseover: (e) => {
          (e.target as L.Path).setStyle({ fillOpacity: 0.55, weight: 2 });
        },
        mouseout: (e) => {
          const isSelected = props.zone_id === selectedZoneId;
          (e.target as L.Path).setStyle({
            fillOpacity: isSelected ? 0.45 : 0.35,
            weight: isSelected ? 2.5 : 0.5,
            color: isSelected ? "#22D3EE" : riskColor(cat),
          });
        },
      });
    },
    [selectedZoneId, onZoneSelect, zoneRisks, isRiskFallback]
  );

  return (
    <div className={className || "relative w-full h-full"}>
      {isRiskFallback ? (
        // API unreachable — serving local GeoJSON fallback
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 border border-amber-500/40 text-[10px] text-amber-400 font-medium pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          Offline · Local Fallback
        </div>
      ) : isDataSample ? (
        // API reachable but data_mode = SAMPLE_MOCK
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 border border-sky-500/40 text-[10px] text-sky-400 font-medium pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
          API Connected · Sample Scenario
        </div>
      ) : (
        // API reachable and data_mode = real/live
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 border border-green-500/40 text-[10px] text-green-400 font-medium pointer-events-none">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
          Backend Reachable · Real Dynamic Data
        </div>
      )}

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
        <MapResizeFix />
        {/* Custom legend */}
        <MapLegend />

        <LayersControl position="topright">
          {/* ── Basemaps ── */}
          <LayersControl.BaseLayer checked name="Terrain">
            <TileLayer
              url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
              attribution='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
              maxZoom={17}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Streets">
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
              maxZoom={19}
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EAP, and the GIS User Community'
              maxZoom={19}
            />
          </LayersControl.BaseLayer>

          {/* ── Risk Zones ── */}
          <LayersControl.Overlay checked name="Risk Grid">
            {gridRisk && (
              <GeoJSON
                key={`risk-${selectedZoneId ?? "none"}-${isRiskFallback ? "fallback" : "live"}-${zoneRisks?.size ?? 0}`}
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
          <LayersControl.Overlay checked name="Roads">
            <>
              {roads?.features.map((f, i) => {
                const props = f.properties as RoadGeoJSONProperties;
                const highwayType = props.highway ?? props.road_type ?? "road";
                const isReal = props.data_type === "REAL_OSM" || geoData.isRealOsm;
                const roadName = props.name || props.ref || (isReal ? "Unnamed road (OSM)" : "Unnamed road");
                const coords = (
                  f.geometry as GeoJSON.LineString
                ).coordinates.map(([lon, lat]) => [lat, lon] as [number, number]);
                const isExcluded = ["steps", "pedestrian", "footway", "path", "cycleway", "corridor", "construction", "proposed"].includes(highwayType);
                const isTrack = highwayType === "track";
                const isNoAccess = props.access === "no" || props.vehicle === "no" || props.motor_vehicle === "no";
                const isPrivate = props.access === "private";
                const roadCategoryLabel = isTrack
                  ? "Track (non-priority)"
                  : isExcluded
                    ? "Pedestrian / non-motorized"
                    : isNoAccess
                      ? "Restricted access (no motor vehicles)"
                      : isPrivate
                        ? "Private / restricted access"
                        : "Motorable-class mapped road";

                return (
                  <Polyline
                    key={props.road_id ?? props.osm_id ?? i}
                    positions={coords}
                    pathOptions={{
                      color: roadColor(highwayType),
                      weight: roadWeight(highwayType),
                      opacity: 0.8,
                      dashArray:
                        highwayType === "local_road" || highwayType === "service" || highwayType === "track" || isExcluded
                          ? "4 4"
                          : undefined,
                    }}
                  >
                    <Popup>
                      <div className="text-xs">
                        <p className="font-semibold">{roadName}</p>
                        <p className="text-slate-500 capitalize">
                          {highwayType.replace(/_/g, " ")} · {roadCategoryLabel}
                        </p>
                        {isReal ? (
                          <div className="mt-1 border-t border-slate-700/50 pt-1">
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                              REAL_OSM · © OSM contributors
                            </span>
                            {props.surface && (
                              <p className="text-slate-400 text-[10px]">Surface: {props.surface}</p>
                            )}
                            {props.access && (
                              <p className="text-amber-400 text-[10px]">Access: {props.access}</p>
                            )}
                            <p className="text-slate-400 text-[10px] mt-1 font-mono">
                              Status: EXPOSED_NOT_VERIFIED_BLOCKED
                            </p>
                            <p className="text-slate-500 text-[9px] italic">
                              Intersecting hazard zone; blockage not verified
                            </p>
                          </div>
                        ) : (
                          <p className="text-amber-500 text-[10px] mt-1 font-mono">
                            SAMPLE MOCK
                          </p>
                        )}
                      </div>
                    </Popup>
                  </Polyline>
                );
              })}
            </>
          </LayersControl.Overlay>

          {/* ── Critical Facilities ── */}
          <LayersControl.Overlay checked name="Critical Facilities">
            <>
              {hospitals?.features.map((f, i) => {
                const props = f.properties as FacilityGeoJSONProperties;
                const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
                const isReal = props.data_type === "REAL_OSM" || geoData.isRealOsm;
                const name = props.name || (isReal ? "Facility (OSM)" : "Unnamed facility");
                const facilityType = (
                  props.category ??
                  props.amenity ??
                  props.facility_type ??
                  "critical_facility"
                ).replace(/_/g, " ");
                return (
                  <CircleMarker
                    key={props.facility_id ?? props.osm_id ?? i}
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
                        <p className="font-semibold">{name}</p>
                        <p className="text-slate-500 capitalize">{facilityType}</p>
                        {props.zone_id && (
                          <p className="text-slate-500">Zone: {props.zone_id}</p>
                        )}
                        {isReal ? (
                          <div className="mt-1 border-t border-slate-700/50 pt-1">
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                              REAL_OSM · © OSM contributors
                            </span>
                            <p className="text-[9px] text-slate-400 italic mt-0.5">
                              Whitelisted & deduplicated critical facility ({facilityType})
                            </p>
                          </div>
                        ) : (
                          <p className="text-amber-500 text-[10px] mt-1 font-mono">
                            SAMPLE MOCK
                          </p>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </>
          </LayersControl.Overlay>

          {/* ── Villages / Communities / Localities ── */}
          <LayersControl.Overlay checked name="Communities">
            <>
              {villages?.features.map((f, i) => {
                const props = f.properties as VillageGeoJSONProperties;
                const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
                const isReal = props.data_type === "REAL_OSM" || geoData.isRealOsm;
                const name = props.name || (isReal ? "Settlement (OSM)" : "Unnamed village");
                const popDisplay = props.population
                  ? `Pop. ${Number(props.population).toLocaleString()}`
                  : props.population_est
                    ? `Pop. est. ${props.population_est.toLocaleString()}`
                    : null;
                return (
                  <CircleMarker
                    key={props.village_id ?? props.osm_id ?? i}
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
                        <p className="font-semibold">{name}</p>
                        {props.place && (
                          <p className="text-slate-500 capitalize">
                            Type: {props.place}
                          </p>
                        )}
                        {popDisplay && (
                          <p className="text-slate-500">{popDisplay}</p>
                        )}
                        {props.zone_id && (
                          <p className="text-slate-500">Zone: {props.zone_id}</p>
                        )}
                        {isReal ? (
                          <div className="mt-1 border-t border-slate-700/50 pt-1">
                            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                              REAL_OSM · © OSM contributors
                            </span>
                            <p className="text-[9px] text-slate-400 italic mt-0.5">
                              OSM locality centre (geographic feature, not population)
                            </p>
                          </div>
                        ) : (
                          <p className="text-amber-500 text-[10px] mt-1 font-mono">
                            SAMPLE MOCK
                          </p>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </>
          </LayersControl.Overlay>

          {/* ── Field Reports ── */}
          <LayersControl.Overlay checked name="Field Reports">
            <>
              {reports?.map((r, i) => {
                return (
                  <CircleMarker
                    key={r.id || i}
                    center={[r.lat, r.lon]}
                    radius={8}
                    pathOptions={{
                      color: "#ffffff",
                      fillColor: "#fbbf24", // amber
                      fillOpacity: 1,
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div className="text-xs">
                        <p className="font-semibold text-amber-500 uppercase">{r.category?.replace("_", " ")}</p>
                        <p className="text-slate-800">{r.description}</p>
                        <p className="text-slate-500 mt-1">Severity: {r.severity}</p>
                        <p className="text-slate-500">Reporter: {r.reporter}</p>
                        {r.zone_id && (
                          <p className="text-slate-500">Zone: {r.zone_id}</p>
                        )}
                        <p className="text-[10px] text-slate-400 mt-1 border-t border-slate-200 pt-1">
                          Status: {r.sync_status} · {new Date(r.timestamp).toLocaleString()}
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
