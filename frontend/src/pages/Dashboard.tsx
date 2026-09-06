// ============================================================
// Dashboard — main page
// Layout: TopBar → (Map 60% | Cards 40%) → bottom report strip
// Phase 1: all cards in placeholder state, map is MapPlaceholder
// Phase 2+: MapPlaceholder → RiskMap (Leaflet)
// Phase 3+: cards receive real data from API hooks
// ============================================================

import { useState } from "react";
import TopBar from "../components/layout/TopBar";
import MapPlaceholder from "../components/map/MapPlaceholder";
import RiskSeverityCard from "../components/dashboard/RiskSeverityCard";
import ForecastCard from "../components/dashboard/ForecastCard";
import ExposureCard from "../components/dashboard/ExposureCard";
import EmergencyPriorityCard from "../components/dashboard/EmergencyPriorityCard";
import WhyNowCard from "../components/dashboard/WhyNowCard";
import ReportList from "../components/reports/ReportList";

export default function Dashboard() {
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-slate-900">
      {/* Top bar */}
      <TopBar districtMeta={null} />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left: Map (flex-grow takes ~60%) ── */}
        <div className="flex-1 p-3 overflow-hidden">
          <MapPlaceholder onZoneSelect={setSelectedZoneId} />
        </div>

        {/* ── Right: Card stack ── */}
        <aside className="w-80 shrink-0 flex flex-col gap-2 p-3 overflow-y-auto border-l border-slate-700/50">
          {/* Selected zone indicator */}
          {selectedZoneId ? (
            <div className="flex items-center justify-between px-3 py-1.5 rounded-md bg-blue-600/10 border border-blue-500/30">
              <span className="text-xs text-blue-400 font-medium">
                Zone {selectedZoneId} selected
              </span>
              <button
                className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                onClick={() => setSelectedZoneId(null)}
              >
                ✕ Clear
              </button>
            </div>
          ) : (
            <div className="px-3 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/50">
              <p className="text-[10px] text-slate-500 text-center">
                Click a zone on the map to see detailed analysis
              </p>
            </div>
          )}

          <RiskSeverityCard zones={[]} selectedZone={null} />
          <ForecastCard forecast={null} zoneId={selectedZoneId} />
          <ExposureCard exposure={null} zoneId={selectedZoneId} />
          <EmergencyPriorityCard priority={null} zoneId={selectedZoneId} />
          <WhyNowCard whyNow={null} zoneId={selectedZoneId} />
        </aside>
      </div>

      {/* ── Bottom: Reports strip ── */}
      <div className="shrink-0 h-44 border-t border-slate-700 bg-slate-850 flex">
        {/* Reports */}
        <div className="flex-1 p-3 overflow-hidden">
          <ReportList reports={[]} />
        </div>

        {/* Status bar */}
        <div className="w-80 shrink-0 border-l border-slate-700 p-3 flex flex-col gap-2">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            System Status
          </h3>
          <div className="flex flex-col gap-1.5">
            {[
              { label: "Risk Engine", status: "Not connected — Phase 4", ok: null },
              { label: "Weather Data", status: "Sample mode", ok: null },
              { label: "OSM Geodata", status: "Phase 2", ok: null },
              { label: "Field Reports", status: "Phase 8", ok: null },
              { label: "Offline Sync", status: "Phase 9", ok: null },
            ].map(({ label, status, ok }) => (
              <div key={label} className="flex items-center justify-between text-xs">
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
        </div>
      </div>
    </div>
  );
}
