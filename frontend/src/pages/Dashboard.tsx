// ============================================================
// Dashboard — main page (Phase 2 update)
// Changes from Phase 1:
//   - MapPlaceholder → RiskMap (Leaflet)
//   - useGeoJSONData hook loads all four sample layers
//   - Zone click → selectedZoneProps state → card data derived via transformers
//   - RiskSeverityCard, ForecastCard, WhyNowCard now show real zone data
//   - ExposureCard, EmergencyPriorityCard remain as Phase 6 placeholders
//   - System Status updated: "OSM Geodata" now green (sample loaded)
// ============================================================

import { useState, useMemo } from "react";
import type { Feature } from "geojson";
import TopBar from "../components/layout/TopBar";
import RiskMap from "../components/map/RiskMap";
import RiskSeverityCard from "../components/dashboard/RiskSeverityCard";
import ForecastCard from "../components/dashboard/ForecastCard";
import ExposureCard from "../components/dashboard/ExposureCard";
import EmergencyPriorityCard from "../components/dashboard/EmergencyPriorityCard";
import WhyNowCard from "../components/dashboard/WhyNowCard";
import ReportList from "../components/reports/ReportList";
import { useGeoJSONData } from "../hooks/useGeoJSONData";
import {
  propsToZone,
  propsToForecast,
  propsToWhyNow,
} from "../utils/zoneTransformers";
import type { ZoneGeoJSONProperties } from "../types/geojson";
import type { Zone } from "../types";

export default function Dashboard() {
  const geoData = useGeoJSONData();
  const [selectedZoneProps, setSelectedZoneProps] =
    useState<ZoneGeoJSONProperties | null>(null);

  // Derive typed card data from raw GeoJSON properties
  const selectedZone = useMemo(
    () => (selectedZoneProps ? propsToZone(selectedZoneProps) : null),
    [selectedZoneProps]
  );
  const forecast = useMemo(
    () => (selectedZoneProps ? propsToForecast(selectedZoneProps) : null),
    [selectedZoneProps]
  );
  const whyNow = useMemo(
    () => (selectedZoneProps ? propsToWhyNow(selectedZoneProps) : null),
    [selectedZoneProps]
  );

  // All zones for district-level breakdown in RiskSeverityCard
  const allZones = useMemo((): Zone[] => {
    if (!geoData.gridRisk) return [];
    return geoData.gridRisk.features
      .filter((f): f is Feature => f.type === "Feature" && !!f.properties)
      .map((f) => propsToZone(f.properties as ZoneGeoJSONProperties));
  }, [geoData.gridRisk]);

  const selectedZoneId = selectedZoneProps?.zone_id ?? null;

  // System status: OSM Geodata turns green once sample data loads
  const osmStatus = geoData.loading
    ? "Loading…"
    : geoData.error
      ? "Load error"
      : "Sample loaded";
  const osmOk = geoData.error ? false : geoData.gridRisk ? true : null;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-900">
      {/* Top bar */}
      <TopBar districtMeta={null} />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left: Map (flex-grow takes ~60%) ── */}
        <div className="flex-1 p-3 overflow-hidden">
          <RiskMap
            geoData={geoData}
            selectedZoneId={selectedZoneId}
            onZoneSelect={setSelectedZoneProps}
          />
        </div>

        {/* ── Right: Card stack ── */}
        <aside className="w-80 shrink-0 flex flex-col gap-2 p-3 overflow-y-auto border-l border-slate-700/50">
          {/* Zone selection indicator */}
          {selectedZoneId ? (
            <div className="flex items-center justify-between px-3 py-1.5 rounded-md bg-blue-600/10 border border-blue-500/30">
              <div>
                <span className="text-xs text-blue-400 font-medium">
                  Zone {selectedZoneId} selected
                </span>
                {selectedZoneProps && (
                  <span
                    className={`ml-2 text-[10px] font-semibold ${
                      selectedZoneProps.risk_category === "VERY_HIGH"
                        ? "text-red-400"
                        : selectedZoneProps.risk_category === "HIGH"
                          ? "text-orange-400"
                          : selectedZoneProps.risk_category === "MODERATE"
                            ? "text-yellow-400"
                            : "text-green-400"
                    }`}
                  >
                    {selectedZoneProps.risk_category.replace("_", " ")}
                  </span>
                )}
              </div>
              <button
                className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                onClick={() => setSelectedZoneProps(null)}
              >
                ✕ Clear
              </button>
            </div>
          ) : (
            <div className="px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/50">
              <p className="text-[10px] text-slate-500 text-center">
                Click a coloured zone on the map to see detailed analysis
              </p>
            </div>
          )}

          <RiskSeverityCard zones={allZones} selectedZone={selectedZone} />
          <ForecastCard forecast={forecast} zoneId={selectedZoneId} />
          <ExposureCard exposure={null} zoneId={selectedZoneId} />
          <EmergencyPriorityCard priority={null} zoneId={selectedZoneId} />
          <WhyNowCard whyNow={whyNow} zoneId={selectedZoneId} />
        </aside>
      </div>

      {/* ── Bottom: Reports + Status strip ── */}
      <div className="shrink-0 h-44 border-t border-slate-700 bg-slate-850 flex">
        {/* Reports */}
        <div className="flex-1 p-3 overflow-hidden">
          <ReportList reports={[]} />
        </div>

        {/* System Status */}
        <div className="w-80 shrink-0 border-l border-slate-700 p-3 flex flex-col gap-2">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            System Status
          </h3>
          <div className="flex flex-col gap-1.5">
            {[
              {
                label: "Risk Engine",
                status: "Not connected — Phase 4",
                ok: null,
              },
              { label: "Weather Data", status: "Sample mode", ok: null },
              { label: "OSM Geodata", status: osmStatus, ok: osmOk },
              { label: "Field Reports", status: "Phase 8", ok: null },
              { label: "Offline Sync", status: "Phase 9", ok: null },
            ].map(({ label, status, ok }) => (
              <div
                key={label}
                className="flex items-center justify-between text-xs"
              >
                <span className="text-slate-500">{label}</span>
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      ok === true
                        ? "bg-green-400"
                        : ok === false
                          ? "bg-red-400"
                          : "bg-slate-600"
                    }`}
                  />
                  <span
                    className={
                      ok === true
                        ? "text-green-400"
                        : ok === false
                          ? "text-red-400"
                          : "text-slate-600"
                    }
                  >
                    {status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Data mode note */}
          <div className="mt-auto text-[10px] text-slate-600 border-t border-slate-700 pt-2">
            Phase 2 · Sample GeoJSON · CartoDB Dark basemap
          </div>
        </div>
      </div>
    </div>
  );
}
