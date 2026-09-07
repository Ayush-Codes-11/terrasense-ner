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
import { Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import RiskMap from "../components/map/RiskMap";
import RiskSeverityCard from "../components/dashboard/RiskSeverityCard";
import ForecastCard from "../components/dashboard/ForecastCard";
import ExposureCard from "../components/dashboard/ExposureCard";
import EmergencyPriorityCard from "../components/dashboard/EmergencyPriorityCard";
import WhyNowCard from "../components/dashboard/WhyNowCard";
import AlertsPanel from "../components/dashboard/AlertsPanel";
import ReportList from "../components/reports/ReportList";
import SideDrawer from "../components/ui/SideDrawer";
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

  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isReportsOpen, setIsReportsOpen] = useState(false);
  const [isDataStatusOpen, setIsDataStatusOpen] = useState(false);

  const pendingReportsCount = localReports.filter(r => r.sync_status !== "SYNCED").length;

  // Find latest retrieved_at from zonesList
  const lastUpdated = useMemo(() => {
    if (!zonesList || zonesList.length === 0) return null;
    let maxTime = "";
    for (const z of zonesList) {
      if (z.data_meta?.freshness) {
        if (z.data_meta.freshness > maxTime) {
          maxTime = z.data_meta.freshness;
        }
      }
    }
    return maxTime || null;
  }, [zonesList]);

  return (
    <div className="flex flex-col h-[100dvh] overflow-hidden bg-[#07111F]">
      <TopBar
        districtMeta={null}
        lastUpdated={lastUpdated}
        isOffline={isRiskFallback}
      />

      <main className="relative flex-1 min-h-0 overflow-hidden">
        <RiskMap
          className="absolute inset-0 h-full w-full z-0"
          geoData={geoData}
          selectedZoneId={selectedZoneId}
          onZoneSelect={setSelectedZoneProps}
          zoneRisks={zoneRisksMap}
          isRiskFallback={isRiskFallback}
          reports={localReports}
        />

        {/* Floating Top Actions */}
        <div className="absolute top-4 right-4 z-[1000] flex flex-wrap gap-2 justify-end pointer-events-none">
          <button 
            className="pointer-events-auto px-3 py-1.5 rounded-md bg-[#101F35]/90 border border-slate-400/20 shadow-lg text-xs font-medium text-slate-200 hover:bg-[#152845] transition-all backdrop-blur-md flex items-center gap-2"
            onClick={() => setIsDataStatusOpen(!isDataStatusOpen)}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${apiOk ? "bg-green-400" : "bg-amber-400"}`}></span>
            Data Status
          </button>
          
          <button 
            className="pointer-events-auto px-3 py-1.5 rounded-md bg-[#101F35]/90 border border-slate-400/20 shadow-lg text-xs font-medium text-slate-200 hover:bg-[#152845] transition-all backdrop-blur-md flex items-center gap-2"
            onClick={() => setIsAlertsOpen(true)}
          >
            <span>🔔</span> Alerts
          </button>
          
          <button 
            className="pointer-events-auto px-3 py-1.5 rounded-md bg-[#101F35]/90 border border-slate-400/20 shadow-lg text-xs font-medium text-slate-200 hover:bg-[#152845] transition-all backdrop-blur-md flex items-center gap-2"
            onClick={() => setIsReportsOpen(true)}
          >
            <span>📋</span> Field Reports
            {pendingReportsCount > 0 && (
              <span className="bg-[#22D3EE]/20 text-[#22D3EE] px-1.5 py-0.5 rounded text-[10px] ml-1">
                {pendingReportsCount}
              </span>
            )}
          </button>

          <Link 
            to="/field-report"
            className="pointer-events-auto px-3 py-1.5 rounded-md bg-[#3B82F6]/90 border border-[#3B82F6]/50 shadow-lg text-xs font-medium text-white hover:bg-[#3B82F6] transition-all backdrop-blur-md"
          >
            + Field Report
          </Link>
        </div>

        {/* Data Status Popover */}
        {isDataStatusOpen && (
          <div className="absolute top-14 right-4 z-[1010] w-[300px] card p-3 flex flex-col gap-2">
            <h3 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide border-b border-slate-700/50 pb-1 mb-1">
              Data Sources & Provenance
            </h3>
            <div className="flex flex-col gap-1 font-mono">
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
                  <span className="text-slate-500 w-16">{label}</span>
                  <span className="text-slate-300 truncate flex-1 px-1">{source}</span>
                  <span className={`px-1.5 py-0.5 rounded-sm border ${
                    prov === "REAL" ? "border-green-500/30 text-green-400 bg-green-500/10" : "border-amber-500/30 text-amber-400 bg-amber-500/10"
                  }`}>{prov}</span>
                </div>
              ))}
            </div>
            <div className="mt-2 border-t border-slate-700/50 pt-2 flex flex-col gap-1 font-mono text-[10px]">
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
        )}

        {/* Selected Zone Intelligence Panel (Right/Bottom) */}
        {selectedZoneId && (
          <aside className="absolute top-28 md:top-16 left-4 right-4 md:left-auto bottom-4 z-[500] md:w-[360px] flex flex-col gap-2 pointer-events-none">
            {/* We make the wrapper pointer-events-none so users can click map through gaps, but make children auto */}
            <div className="pointer-events-auto flex items-center justify-between px-3 py-2 rounded-xl bg-[#101F35]/90 border border-[#3B82F6]/30 shadow-lg backdrop-blur-md">
              <div className="flex items-center gap-2">
                <span className="text-sm text-[#22D3EE] font-bold tracking-wide">
                  ZONE {selectedZoneId}
                </span>
                {selectedZone && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${
                      selectedZone.risk === "VERY_HIGH"
                        ? "text-red-400 border-red-500/30 bg-red-500/10"
                        : selectedZone.risk === "HIGH"
                          ? "text-orange-400 border-orange-500/30 bg-orange-500/10"
                          : selectedZone.risk === "MODERATE"
                            ? "text-yellow-400 border-yellow-500/30 bg-yellow-500/10"
                            : "text-green-400 border-green-500/30 bg-green-500/10"
                    }`}
                  >
                    {selectedZone.risk.replace("_", " ")}
                  </span>
                )}
                {forecastLoading && (
                  <svg className="w-3 h-3 text-[#22D3EE] animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                )}
              </div>
              <button
                className="text-slate-400 hover:text-white bg-slate-800/50 hover:bg-slate-700/50 p-1 rounded transition-colors"
                onClick={() => setSelectedZoneProps(null)}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="pointer-events-auto flex-1 overflow-y-auto flex flex-col gap-2 pb-4 scrollbar-hide">
              <RiskSeverityCard zones={zonesList} selectedZone={selectedZone} />
              <EmergencyPriorityCard priority={priority} zoneId={selectedZoneId} />
              <WhyNowCard whyNow={whyNow} zoneId={selectedZoneId} />
              <ForecastCard forecast={forecast} zoneId={selectedZoneId} />
              <ExposureCard exposure={exposure} zoneId={selectedZoneId} />
            </div>
          </aside>
        )}
      </main>

      <SideDrawer 
        isOpen={isAlertsOpen} 
        onClose={() => setIsAlertsOpen(false)} 
        title="Active Alerts"
      >
        <AlertsPanel />
      </SideDrawer>

      <SideDrawer 
        isOpen={isReportsOpen} 
        onClose={() => setIsReportsOpen(false)} 
        title="Field Reports"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3 text-xs">
            {!isOnline ? (
              <span className="text-amber-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                Offline
              </span>
            ) : (
              <span className="text-green-400 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                Online
              </span>
            )}
          </div>
          <Link to="/field-report" className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs transition-colors">
            + New Report
          </Link>
        </div>
        <ReportList reports={localReports} />
      </SideDrawer>
    </div>
  );
}
