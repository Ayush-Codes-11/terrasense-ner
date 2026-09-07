// ============================================================
// RiskSeverityCard — current district-level risk summary
// Phase 1: shows placeholder state
// Phase 3+: receives real Zone[] from /risk/current
// ============================================================

import type { Zone } from "../../types";
import { RISK_BG_CLASSES, RISK_LABEL } from "../../utils/risk";
import DataSourceBadge from "../common/DataSourceBadge";

interface RiskSeverityCardProps {
  zones?: Zone[];
  selectedZone?: Zone | null;
}

function RiskBar({
  level,
  count,
  total,
}: {
  level: string;
  count: number;
  total: number;
}) {
  const colors: Record<string, string> = {
    LOW: "bg-green-500",
    MODERATE: "bg-yellow-500",
    HIGH: "bg-orange-500",
    VERY_HIGH: "bg-red-500",
  };
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 text-slate-400 shrink-0">
        {level.replace("_", " ")}
      </span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${colors[level]} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-5 text-slate-300 text-right shrink-0">{count}</span>
    </div>
  );
}

export default function RiskSeverityCard({
  zones = [],
  selectedZone,
}: RiskSeverityCardProps) {
  const counts = { LOW: 0, MODERATE: 0, HIGH: 0, VERY_HIGH: 0 };
  zones.forEach((z) => counts[z.risk]++);
  const total = zones.length;

  // Dominant risk = highest category with any zones
  const dominantRisk =
    counts.VERY_HIGH > 0
      ? "VERY_HIGH"
      : counts.HIGH > 0
        ? "HIGH"
        : counts.MODERATE > 0
          ? "MODERATE"
          : "LOW";

  const displayZone = selectedZone ?? null;
  const isPlaceholder = total === 0;

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Risk Severity
          </h2>
          <p className="text-[10px] text-slate-600 mt-0.5">
            {displayZone ? `Zone ${displayZone.zone_id}` : "District Overview"}
          </p>
        </div>
        <DataSourceBadge
          source={displayZone?.data_meta.source ?? "unavailable"}
        />
      </div>

      {/* Dominant risk badge or placeholder */}
      {isPlaceholder ? (
        <div className="flex flex-col items-center justify-center py-4 gap-2">
          <div className="w-12 h-12 rounded-full bg-slate-700/60 border-2 border-dashed border-slate-600 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-slate-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <p className="text-xs text-slate-500 text-center">
            No risk data yet
            <br />
            <span className="text-[10px] text-slate-600">
              Phase 3 connects live data
            </span>
          </p>
        </div>
      ) : (
        <>
          {/* Dominant risk */}
          <div className="flex items-center gap-3">
            <span
              className={`risk-badge text-base px-3 py-1.5 ${RISK_BG_CLASSES[dominantRisk]}`}
            >
              {RISK_LABEL[dominantRisk]}
            </span>
            {displayZone && (
              <div>
                <div className="text-[9px] text-slate-500 uppercase tracking-wide">
                  Risk Score
                </div>
                <div className="text-xl font-bold text-white font-mono">
                  {displayZone.risk_score.toFixed(2)}
                </div>
              </div>
            )}
          </div>

          {/* Zone breakdown */}
          <div className="flex flex-col gap-1.5">
            {(["VERY_HIGH", "HIGH", "MODERATE", "LOW"] as const).map((r) => (
              <RiskBar key={r} level={r} count={counts[r]} total={total} />
            ))}
          </div>
          <p className="text-[10px] text-slate-600 border-t border-slate-700 pt-2">
            {total} zones analysed
          </p>
        </>
      )}
    </div>
  );
}
