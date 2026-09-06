// ============================================================
// ExposureCard — road exposure status + village/facility proximity
// Phase 6: displays real OSM exposure metrics & non-blockage guarantee
//
// KEY RULE: "blocked" is false by default.
// A road is only shown as blocked when a verified field report confirms it.
// ============================================================

import type { ExposureData } from "../../types";
import DataSourceBadge from "../common/DataSourceBadge";

interface ExposureCardProps {
  exposure?: ExposureData | null;
  zoneId?: string | null;
}

export default function ExposureCard({ exposure, zoneId }: ExposureCardProps) {
  const isPlaceholder = !exposure;

  const roadKm = exposure?.summary?.roads_exposed_km ?? 0;
  const roadCount = exposure?.summary?.roads_exposed ?? 0;
  const villageCount = exposure?.summary?.villages_exposed ?? 0;
  const facilityCount = exposure?.summary?.hospitals_exposed ?? 0;
  const isReal = exposure?.exposure_features === "REAL_OSM";

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Infrastructure Exposure
          </h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {zoneId ? `Zone ${zoneId} spatial intersection` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={exposure?.data_meta?.source ?? "unavailable"} />
      </div>

      {/* Mixed Provenance / Status tag */}
      <div className="flex items-center justify-between px-2 py-1 bg-slate-900/60 rounded border border-slate-700/50 text-[10px]">
        <span className="text-slate-400 font-medium">
          {isReal ? "OSM snapshot + prototype hazard grid" : "Sample fallback geodata"}
        </span>
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
          {isReal ? "PROTOTYPE MIXED" : "SAMPLE"}
        </span>
      </div>

      {isPlaceholder ? (
        <div className="flex flex-col items-center justify-center py-5 gap-2">
          <div className="grid grid-cols-3 gap-2 w-full">
            {["Roads", "Settlements", "Facilities"].map((t) => (
              <div
                key={t}
                className="flex flex-col items-center gap-1 p-2 rounded-lg bg-slate-900/40 border border-dashed border-slate-700/50"
              >
                <div className="text-base">
                  {t === "Roads" ? "🛣" : t === "Settlements" ? "🏘" : "🏥"}
                </div>
                <div className="w-8 h-3 bg-slate-800 rounded" />
                <span className="text-[9px] text-slate-500">{t}</span>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-500 text-center">
            Click a zone on the map to compute real OSM exposure
          </p>
        </div>
      ) : (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-3 gap-2">
            <div className="flex flex-col items-center p-2 rounded bg-slate-900/50 border border-slate-700/60">
              <span className="text-sm">🛣</span>
              <span className="text-sm font-bold text-white mt-0.5">
                {roadKm.toFixed(2)} <span className="text-[9px] font-normal text-slate-400">km</span>
              </span>
              <span className="text-[9px] text-slate-400">Roads exposed</span>
              <span className="text-[8px] text-slate-500">({roadCount} segments)</span>
            </div>

            <div className="flex flex-col items-center p-2 rounded bg-slate-900/50 border border-slate-700/60">
              <span className="text-sm">🏘</span>
              <span className="text-sm font-bold text-white mt-0.5">{villageCount}</span>
              <span className="text-[9px] text-slate-400">Settlements</span>
              <span className="text-[8px] text-slate-500">in hazard zone</span>
            </div>

            <div className="flex flex-col items-center p-2 rounded bg-slate-900/50 border border-slate-700/60">
              <span className="text-sm">🏥</span>
              <span className="text-sm font-bold text-white mt-0.5">{facilityCount}</span>
              <span className="text-[9px] text-slate-400">Critical facilities</span>
              <span className="text-[8px] text-slate-500">hospitals/police</span>
            </div>
          </div>

          {/* Strict Non-blockage guarantee */}
          <div className="flex items-start gap-1.5 text-[10px] text-slate-400 bg-amber-500/10 rounded px-2.5 py-1.5 border border-amber-500/20">
            <span className="text-amber-400 font-semibold shrink-0">EXPOSED</span>
            <p className="leading-tight text-slate-300">
              Roads are classified as <span className="text-amber-300 font-medium">EXPOSED_NOT_VERIFIED_BLOCKED</span>.
              Zero roads are marked blocked without a verified field officer report.
            </p>
          </div>

          {/* Sample Features in zone */}
          {((exposure.roads && exposure.roads.length > 0) || (exposure.critical_facilities && exposure.critical_facilities.length > 0)) && (
            <div className="max-h-28 overflow-y-auto flex flex-col gap-1 pr-1 border-t border-slate-700/40 pt-1.5">
              <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wider">
                Intersecting Features (Sample)
              </span>
              {exposure.critical_facilities?.slice(0, 3).map((f) => (
                <div key={f.feature_id} className="flex items-center justify-between text-[10px] text-slate-300 py-0.5">
                  <span className="truncate max-w-[170px]">🏥 {f.name || `Unnamed ${f.category}`}</span>
                  <span className="text-[9px] px-1 rounded bg-slate-800 text-slate-400 capitalize">{f.category}</span>
                </div>
              ))}
              {exposure.roads?.slice(0, 3).map((r) => (
                <div key={r.feature_id} className="flex items-center justify-between text-[10px] text-slate-300 py-0.5">
                  <span className="truncate max-w-[170px]">🛣 {r.name || `Unnamed ${r.highway}`}</span>
                  <span className="text-[9px] text-slate-400 font-mono">{r.length_km.toFixed(2)} km</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Attribution footer */}
      <p className="text-[9px] text-slate-500 border-t border-slate-700/60 pt-2 leading-tight">
        © OpenStreetMap contributors · Geodesic clipping via pyproj · Prototype spatial exposure model
      </p>
    </div>
  );
}
