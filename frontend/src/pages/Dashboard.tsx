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

import { useState, useMemo, useEffect } from "react";
import type { Feature } from "geojson";
import TopBar from "../components/layout/TopBar";
import RiskMap from "../components/map/RiskMap";
import RiskSeverityCard from "../components/dashboard/RiskSeverityCard";
import ForecastCard from "../components/dashboard/ForecastCard";
import ExposureCard from "../components/dashboard/ExposureCard";
import EmergencyPriorityCard from "../components/dashboard/EmergencyPriorityCard";
import WhyNowCard from "../components/dashboard/WhyNowCard";
import AlertsPanel from "../components/dashboard/AlertsPanel";
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

  const [localReports, setLocalReports] = useState<any[]>([]);
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);

  useEffect(() => {
    const updateOnlineStatus = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    return () => {
      window.removeEventListener("online", updateOnlineStatus);
      window.removeEventListener("offline", updateOnlineStatus);
    };
  }, []);

  // Load local reports from IndexedDB on mount
  useEffect(() => {
    import("../services/db").then(({ getLocalReports, syncPendingReports }) => {
      // Sync in background first
      if (navigator.onLine) {
        syncPendingReports().catch(console.error);
      }
      
      getLocalReports()
        .then((saved) => {
          setLocalReports(saved || []);
        })
        .catch((e) => {
          console.error("Failed to load local reports", e);
        });
    });
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-900">
      {/* Top bar */}
      <TopBar districtMeta={null} />

      {/* Main content */}
      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden overflow-y-auto lg:overflow-y-hidden">
        {/* ── Left: Map ── */}
        <div className="h-[55vh] lg:h-auto lg:flex-1 p-3 shrink-0 relative min-h-[400px]">
          <RiskMap
            geoData={geoData}
            selectedZoneId={selectedZoneId}
            onZoneSelect={setSelectedZoneProps}
            zoneRisks={zoneRisksMap}
            isRiskFallback={isRiskFallback}
          />
        </div>

        {/* ── Right: Card stack ── */}
        <aside className="w-full lg:w-96 shrink-0 flex flex-col gap-2 p-3 overflow-y-auto border-t lg:border-t-0 lg:border-l border-slate-700/50">
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

      {/* ── Bottom: Reports + Alerts + Status strip ── */}
      <div className="shrink-0 flex flex-col lg:flex-row border-t border-slate-700 bg-slate-900 lg:h-44 h-auto max-h-[50vh] lg:max-h-none overflow-y-auto lg:overflow-y-hidden">
        {/* Field Reports (Left) */}
        <div className="flex-1 lg:border-r border-slate-700 p-3 overflow-hidden flex flex-col bg-slate-800/20 min-h-[150px]">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
              Field Reports
            </h3>
            <div className="flex items-center gap-3 text-[10px]">
              {!isOnline ? (
                <span className="text-amber-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                  Offline
                </span>
              ) : null}
              {localReports.filter(r => r.sync_status !== "SYNCED").length > 0 && (
                <span className="text-blue-400 font-medium">
                  {localReports.filter(r => r.sync_status !== "SYNCED").length} pending sync
                </span>
              )}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto lg:overflow-hidden">
            <ReportList reports={localReports} />
          </div>
        </div>

        {/* Alerts Panel (Middle) */}
        <div className="w-full lg:w-80 shrink-0 overflow-y-auto border-t lg:border-t-0 border-slate-700 max-h-48 lg:max-h-none">
          <AlertsPanel />
        </div>

        {/* Data Provenance & Status (Right) */}
        <div className="w-full lg:w-80 shrink-0 border-t lg:border-t-0 lg:border-l border-slate-700 p-3 flex flex-col gap-2 bg-slate-900/50">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Data Sources & Provenance
          </h3>
          <div className="flex flex-col gap-1.5 font-mono">
            {[
              { label: "Basemap", source: "OpenTopoMap", prov: "REAL" },
              { label: "Elevation", source: "Copernicus GLO-30", prov: "REAL" },
              { label: "Roads", source: "OpenStreetMap", prov: "REAL" },
              { label: "Facilities", source: "OpenStreetMap", prov: "REAL" },
              { label: "Inventory", source: "GSI", prov: "REAL" },
              { label: "Rainfall", source: "GPM-compatible", prov: "SAMPLE" },
              { label: "Soil", source: "Prototype input", prov: "SAMPLE" },
            ].map(({ label, source, prov }) => (
              <div key={label} className="flex items-center justify-between text-[10px]">
                <span className="text-slate-500 w-20">{label}</span>
                <span className="text-slate-300 truncate flex-1 px-1">{source}</span>
                <span className={`px-1.5 rounded-sm border ${
                  prov === "REAL" ? "border-green-500/30 text-green-400 bg-green-500/10" : "border-amber-500/30 text-amber-400 bg-amber-500/10"
                }`}>{prov}</span>
              </div>
            ))}
          </div>

          <div className="mt-auto border-t border-slate-700/50 pt-2 flex flex-col gap-1 font-mono text-[10px]">
            <div className="flex justify-between items-center">
              <span className="text-slate-500">Risk Engine</span>
              <span className={riskEngineOk ? "text-green-400" : "text-amber-400"}>{riskEngineStatus}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500">Backend API</span>
              <span className={apiOk ? "text-green-400" : "text-amber-400"}>{apiStatus}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
