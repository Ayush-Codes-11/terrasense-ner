// ============================================================
// Dashboard — main page (Phase 4 update)
// Changes from Phase 3:
//   - useAllZoneRisks hook fetches all 25 zones' current risk from
//     FastAPI (/risk/current), dynamically computed by ml.prototype_scorer.
//   - RiskMap receives zoneRisksMap so map polygon colours reflect
//     computed prototype scores rather than precomputed GeoJSON attributes.
//   - useZoneDetails fetches both forecast and computed zone risk + contributors.
//   - WhyNowCard displays real prototype feature contributions.
//   - System Status updates: "Risk Engine" -> "Prototype scorer active" (green).
//   - Graceful fallback: If backend fails, visibly labels "Sample fallback".
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
import { useAllZoneRisks } from "../hooks/useAllZoneRisks";
import { useZoneDetails } from "../hooks/useZoneDetails";
import { propsToZone } from "../utils/zoneTransformers";
import type { ZoneGeoJSONProperties } from "../types/geojson";
import type { Zone } from "../types";

export default function Dashboard() {
  const geoData = useGeoJSONData();
  const [selectedZoneProps, setSelectedZoneProps] =
    useState<ZoneGeoJSONProperties | null>(null);

  const selectedZoneId = selectedZoneProps?.zone_id ?? null;

  // Derive fallback zones from raw GeoJSON (used if backend is down)
  const fallbackZones = useMemo((): Zone[] => {
    if (!geoData.gridRisk) return [];
    return geoData.gridRisk.features
      .filter((f): f is Feature => f.type === "Feature" && !!f.properties)
      .map((f) => propsToZone(f.properties as ZoneGeoJSONProperties));
  }, [geoData.gridRisk]);

  // Fetch all zone risks computed by backend prototype scorer
  const {
    zoneRisksMap,
    zonesList,
    isFallback: isRiskFallback,
    apiOnline: allZonesApiOnline,
  } = useAllZoneRisks(fallbackZones);

  // Fetch selected zone forecast & current risk details (with contributors, exposure, priority)
  const {
    forecast,
    selectedZone: apiSelectedZone,
    whyNow,
    exposure,
    priority,
    loading: forecastLoading,
    apiOnline: zoneDetailsApiOnline,
    source: forecastSource,
  } = useZoneDetails(selectedZoneId, selectedZoneProps);

  // Use API selected zone if available, else local fallback
  const selectedZone = useMemo(() => {
    if (apiSelectedZone) return apiSelectedZone;
    if (selectedZoneId && zoneRisksMap.has(selectedZoneId)) {
      return zoneRisksMap.get(selectedZoneId)!;
    }
    return selectedZoneProps ? propsToZone(selectedZoneProps) : null;
  }, [apiSelectedZone, selectedZoneId, zoneRisksMap, selectedZoneProps]);

  // Consolidated API health status
  const apiOnline =
    allZonesApiOnline === true || zoneDetailsApiOnline === true
      ? true
      : allZonesApiOnline === false && zoneDetailsApiOnline === false
        ? false
        : allZonesApiOnline ?? zoneDetailsApiOnline;

  // System status indicators
  const geoExposureStatus = geoData.loading
    ? "Loading…"
    : geoData.error
      ? "Load error"
      : geoData.osmStatus === "OSM snapshot"
        ? "OSM snapshot"
        : geoData.osmStatus === "Cached OSM"
          ? "Cached OSM"
          : "Sample fallback";
  const geoExposureOk = geoData.error ? false : geoData.isRealOsm ? true : false;

  const apiStatus =
    apiOnline === true
      ? "Connected"
      : apiOnline === false
        ? "Offline (Sample fallback)"
        : "Checking…";
  const apiOk = apiOnline === true ? true : apiOnline === false ? false : null;

  const riskEngineStatus =
    apiOnline === true
      ? "Prototype scorer active"
      : apiOnline === false
        ? "Sample fallback (engine offline)"
        : "Initialising…";
  const riskEngineOk =
    apiOnline === true ? true : apiOnline === false ? false : null;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-900">
      {/* Top bar */}
      <TopBar districtMeta={null} />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left: Map ── */}
        <div className="flex-1 p-3 overflow-hidden">
          <RiskMap
            geoData={geoData}
            selectedZoneId={selectedZoneId}
            onZoneSelect={setSelectedZoneProps}
            zoneRisks={zoneRisksMap}
            isRiskFallback={isRiskFallback}
          />
        </div>

        {/* ── Right: Card stack ── */}
        <aside className="w-80 shrink-0 flex flex-col gap-2 p-3 overflow-y-auto border-l border-slate-700/50">
          {/* Zone selection indicator */}
          {selectedZoneId ? (
            <div className="flex items-center justify-between px-3 py-1.5 rounded-md bg-blue-600/10 border border-blue-500/30">
              <div className="flex items-center gap-2">
                <span className="text-xs text-blue-400 font-medium">
                  Zone {selectedZoneId} selected
                </span>
                {selectedZone && (
                  <span
                    className={`text-[10px] font-semibold ${
                      selectedZone.risk === "VERY_HIGH"
                        ? "text-red-400"
                        : selectedZone.risk === "HIGH"
                          ? "text-orange-400"
                          : selectedZone.risk === "MODERATE"
                            ? "text-yellow-400"
                            : "text-green-400"
                    }`}
                  >
                    {selectedZone.risk.replace("_", " ")}
                  </span>
                )}
                {/* Data source badge */}
                {forecastSource && (
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded border ${
                      forecastSource === "api"
                        ? "bg-green-500/10 text-green-400 border-green-500/30"
                        : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    }`}
                  >
                    {forecastSource === "api"
                      ? "Prototype Scorer"
                      : "Sample fallback"}
                  </span>
                )}
                {forecastLoading && (
                  <svg
                    className="w-3 h-3 text-blue-400 animate-spin"
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
                )}
              </div>
              <button
                className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                onClick={() => setSelectedZoneProps(null)}
              >
                ✕
              </button>
            </div>
          ) : (
            <div className="px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/50">
              <p className="text-[10px] text-slate-500 text-center">
                Click a coloured zone on the map to see detailed analysis
              </p>
            </div>
          )}

          <RiskSeverityCard zones={zonesList} selectedZone={selectedZone} />
          <ForecastCard forecast={forecast} zoneId={selectedZoneId} />
          <ExposureCard exposure={exposure} zoneId={selectedZoneId} />
          <EmergencyPriorityCard priority={priority} zoneId={selectedZoneId} />
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
                label: "FastAPI Backend",
                status: apiStatus,
                ok: apiOk,
              },
              {
                label: "Risk Engine",
                status: riskEngineStatus,
                ok: riskEngineOk,
              },
              { label: "Weather Data", status: "Sample scenario", ok: null },
              {
                label: "Geospatial Exposure",
                status: geoExposureStatus,
                ok: geoExposureOk,
              },
              { label: "Field Reports", status: "Phase 8", ok: null },
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
                          ? "bg-amber-400"
                          : "bg-slate-600"
                    }`}
                  />
                  <span
                    className={
                      ok === true
                        ? "text-green-400"
                        : ok === false
                          ? "text-amber-400"
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
            Phase 4 · Prototype Scorer · FastAPI backend · Sample GeoJSON
          </div>
        </div>
      </div>
    </div>
  );
}
