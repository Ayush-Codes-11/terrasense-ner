// ============================================================
// ReportList — sidebar list of recent field reports
// Phase 1: placeholder
// Phase 8+: receives FieldReport[] from /reports
// ============================================================

import type { FieldReport } from "../../types";
import { formatDateTime } from "../../utils/risk";

interface ReportListProps {
  reports?: FieldReport[];
}

const TYPE_LABELS: Record<string, string> = {
  slope_crack: "Slope Crack",
  debris: "Debris",
  road_blockage: "Road Blockage",
  landslide: "Landslide",
  other: "Other",
};

const TYPE_ICONS: Record<string, string> = {
  slope_crack: "🪨",
  debris: "⛰",
  road_blockage: "🚧",
  landslide: "⚠️",
  other: "📍",
};

const SYNC_CLASSES: Record<string, string> = {
  synced: "text-green-400",
  pending: "text-amber-400",
  failed: "text-red-400",
};

export default function ReportList({ reports = [] }: ReportListProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          Field Reports
        </h3>
        {reports.length > 0 && (
          <span className="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">
            {reports.length}
          </span>
        )}
      </div>

      {reports.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 py-4">
          <div className="text-2xl opacity-30">📋</div>
          <p className="text-xs text-slate-600 text-center">
            No field reports yet
            <br />
            <span className="text-[10px]">
              Phase 8 enables geo-tagged reporting
            </span>
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto flex flex-col gap-1.5">
          {reports.map((r) => (
            <div
              key={r.report_id}
              className="flex items-start gap-2 p-2 rounded-lg bg-slate-900/40 border border-slate-700/40 hover:border-slate-600/60 transition-colors"
            >
              <span className="text-base shrink-0">
                {TYPE_ICONS[r.report_type] ?? "📍"}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-medium text-slate-300 truncate">
                    {TYPE_LABELS[r.report_type] ?? r.report_type}
                  </span>
                  {r.sync_status && (
                    <span
                      className={`text-[10px] shrink-0 ${SYNC_CLASSES[r.sync_status]}`}
                    >
                      {r.sync_status === "synced"
                        ? "✓ Synced"
                        : r.sync_status === "pending"
                          ? "⏳ Pending"
                          : "✗ Failed"}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 truncate">
                  {r.description}
                </p>
                <p className="text-[10px] text-slate-600">
                  {formatDateTime(r.submitted_at)}
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
