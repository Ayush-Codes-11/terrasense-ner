// ============================================================
// ExposureCard — road exposure status + village/hospital proximity
// Phase 1: placeholder
// Phase 6+: receives ExposureData from /exposure/{zone_id}
//
// KEY RULE (from plan): "blocked" is false by default.
// A road is only shown as blocked when a verified field report confirms it.
// ============================================================

import type { ExposureData, ExposedFeature } from "../../types";
import DataSourceBadge from "../common/DataSourceBadge";

interface ExposureCardProps {
  exposure?: ExposureData | null;
  zoneId?: string | null;
}

const ICONS: Record<string, string> = {
  road: "🛣",
  village: "🏘",
  hospital: "🏥",
  other: "📍",
};

function FeatureRow({ f }: { f: ExposedFeature }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-slate-700/40 last:border-0 text-xs">
      <div className="flex items-center gap-2">
        <span>{ICONS[f.type]}</span>
        <span className="text-slate-300 truncate max-w-[140px]">{f.name}</span>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        {f.exposed && !f.blocked && (
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-orange-500/20 text-orange-400 border border-orange-500/30">
            Exposed
          </span>
        )}
        {f.blocked && (
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 font-semibold">
            Blocked ✓
          </span>
        )}
        {!f.exposed && !f.blocked && (
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-green-500/20 text-green-400 border border-green-500/30">
            Clear
          </span>
        )}
      </div>
    </div>
  );
}

export default function ExposureCard({ exposure, zoneId }: ExposureCardProps) {
  const isPlaceholder = !exposure;

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Road &amp; Infrastructure Exposure
          </h2>
          <p className="text-[10px] text-slate-600 mt-0.5">
            {zoneId ? `Zone ${zoneId}` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={exposure?.data_meta.source ?? "unavailable"} />
      </div>

      {/* Blocked = verified-only note */}
      <div className="text-[10px] text-slate-500 bg-slate-900/50 rounded px-2 py-1 border border-slate-700/50">
        🔒 "Blocked" status is set only by a verified field report. Exposed =
        geometrically within risk zone.
      </div>

      {isPlaceholder ? (
        <div className="flex flex-col items-center justify-center py-5 gap-2">
          <div className="grid grid-cols-3 gap-3 w-full">
            {["roads", "villages", "hospitals"].map((t) => (
              <div
                key={t}
                className="flex flex-col items-center gap-1 p-2.5 rounded-lg bg-slate-900/40 border border-dashed border-slate-700/50"
              >
                <div className="text-lg">
                  {t === "roads" ? "🛣" : t === "villages" ? "🏘" : "🏥"}
                </div>
                <div className="w-6 h-3 bg-slate-800 rounded" />
                <span className="text-[10px] text-slate-600 capitalize">{t}</span>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-600">
            Phase 6 enables OSM-based spatial intersection
          </p>
        </div>
      ) : (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-3 gap-2">
            <div className="flex flex-col items-center p-2 rounded bg-slate-900/40 border border-slate-700/50">
              <span className="text-base">🛣</span>
              <span className="text-sm font-bold text-white">
                {exposure.summary.roads_exposed}
              </span>
              <span className="text-[10px] text-slate-500">Roads exposed</span>
              {exposure.summary.roads_blocked > 0 && (
                <span className="text-[10px] text-red-400 font-medium">
                  {exposure.summary.roads_blocked} blocked
                </span>
              )}
            </div>
            <div className="flex flex-col items-center p-2 rounded bg-slate-900/40 border border-slate-700/50">
              <span className="text-base">🏘</span>
              <span className="text-sm font-bold text-white">
                {exposure.summary.villages_exposed}
              </span>
              <span className="text-[10px] text-slate-500">Villages</span>
            </div>
            <div className="flex flex-col items-center p-2 rounded bg-slate-900/40 border border-slate-700/50">
              <span className="text-base">🏥</span>
              <span className="text-sm font-bold text-white">
                {exposure.summary.hospitals_exposed}
              </span>
              <span className="text-[10px] text-slate-500">Facilities</span>
            </div>
          </div>

          {/* Feature list */}
          <div className="max-h-28 overflow-y-auto">
            {exposure.exposed_features.map((f) => (
              <FeatureRow key={f.feature_id} f={f} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
