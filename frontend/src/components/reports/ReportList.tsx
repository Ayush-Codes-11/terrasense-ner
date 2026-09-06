// ============================================================
// ReportList — sidebar list of recent field reports
// Phase 1: placeholder
// Phase 8+: receives FieldReport[] from /reports
// ============================================================

import { formatDateTime } from "../../utils/risk";

interface ReportListProps {
  reports?: any[];
}

const TYPE_LABELS: Record<string, string> = {
  slope_crack: "Slope Crack",
  debris: "Debris",
  road_blockage: "Road Blockage",
  landslide: "Landslide",
  flooding: "Flooding",
  cracks_slope_movement: "Slope Movement",
  other: "Other",
};

const TYPE_ICONS: Record<string, string> = {
  slope_crack: "🪨",
  debris: "⛰",
  road_blockage: "🚧",
  landslide: "⚠️",
  flooding: "🌊",
  cracks_slope_movement: "🪨",
  other: "📍",
};

const SYNC_CLASSES: Record<string, string> = {
  SYNCED: "text-green-400",
  SYNC_PENDING: "text-amber-400",
  LOCAL_ONLY: "text-amber-400",
  SYNCING: "text-blue-400",
  SYNC_FAILED: "text-red-400",
};

export default function ReportList({ reports = [] }: ReportListProps) {
  return (
    <div className="flex flex-col h-full">
      {reports.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 py-4">
          <div className="text-2xl opacity-30">📋</div>
          <p className="text-xs text-slate-600 text-center">
            No field reports yet
            <br />
            <span className="text-[10px]">
              Use /field-report to submit
            </span>
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto flex flex-col gap-1.5">
          {reports.map((r) => (
            <div
              key={r.id}
              className="flex items-start gap-2 p-2 rounded-lg bg-slate-900/40 border border-slate-700/40 hover:border-slate-600/60 transition-colors"
            >
              <span className="text-base shrink-0">
                {TYPE_ICONS[r.category] ?? "📍"}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-medium text-slate-300 truncate">
                    {TYPE_LABELS[r.category] ?? r.category}
                  </span>
                  {r.sync_status && (
                    <span
                      className={`text-[10px] shrink-0 ${SYNC_CLASSES[r.sync_status]}`}
                    >
                      {r.sync_status === "SYNCED"
                        ? "✓ Synced"
                        : r.sync_status === "SYNC_FAILED"
                          ? "✗ Failed"
                          : "⏳ Pending"}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 truncate">
                  {r.description}
                </p>
                <p className="text-[10px] text-slate-600">
                  {formatDateTime(r.timestamp)}
                  {r.zone_id && ` · Zone ${r.zone_id}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
