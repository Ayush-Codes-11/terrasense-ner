// ============================================================
// EmergencyPriorityCard — Prototype Decision-Support Priority
// Phase 1: placeholder
// Phase 6+: receives PriorityData from /priority/{zone_id}
//
// IMPORTANT: Always displays "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL"
// This is not a government or operational classification.
// ============================================================

import type { PriorityData, PriorityLevel } from "../../types";
import { PRIORITY_BG_CLASSES } from "../../utils/risk";
import DataSourceBadge from "../common/DataSourceBadge";

interface EmergencyPriorityCardProps {
  priority?: PriorityData | null;
  zoneId?: string | null;
}

const PRIORITY_ICONS: Record<PriorityLevel, string> = {
  LOW: "🟢",
  MEDIUM: "🔵",
  HIGH: "🟠",
  CRITICAL: "🔴",
};

const PRIORITY_DESC: Record<PriorityLevel, string> = {
  LOW: "Situation is stable. Continue monitoring.",
  MEDIUM: "Elevated risk. Pre-position resources.",
  HIGH: "Significant exposure. Alert local officials.",
  CRITICAL: "Immediate action recommended. Evacuate if warranted.",
};

export default function EmergencyPriorityCard({
  priority,
  zoneId,
}: EmergencyPriorityCardProps) {
  const isPlaceholder = !priority;

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Decision-Support Priority
          </h2>
          <p className="text-[10px] text-slate-600 mt-0.5">
            {zoneId ? `Zone ${zoneId}` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={priority?.data_meta.source ?? "unavailable"} />
      </div>

      {/* Disclaimer — always visible */}
      <div className="flex items-start gap-1.5 bg-slate-900/60 rounded px-2 py-1.5 border border-slate-700/50">
        <svg
          className="w-3 h-3 text-slate-500 shrink-0 mt-0.5"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
        <p className="text-[10px] text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-400">
            PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL.
          </span>{" "}
          Outputs are from a prototype scoring model and must not be used for
          operational disaster response without expert validation.
        </p>
      </div>

      {isPlaceholder ? (
        <div className="flex flex-col items-center justify-center py-4 gap-3">
          <div className="w-12 h-12 rounded-full bg-slate-700/60 border-2 border-dashed border-slate-600 flex items-center justify-center text-xl">
            ?
          </div>
          <p className="text-xs text-slate-500 text-center">
            Priority calculated after zone selection
            <br />
            <span className="text-[10px] text-slate-600">
              Phase 6 enables spatial exposure logic
            </span>
          </p>
        </div>
      ) : (
        <>
          {/* Priority badge */}
          <div className="flex items-center gap-3">
            <div className="text-3xl">{PRIORITY_ICONS[priority.priority]}</div>
            <div>
              <span
                className={`risk-badge text-sm px-3 py-1 ${PRIORITY_BG_CLASSES[priority.priority]}`}
              >
                {priority.priority}
              </span>
              <p className="text-[11px] text-slate-400 mt-1">
                {PRIORITY_DESC[priority.priority]}
              </p>
            </div>
          </div>

          {/* Reasoning list */}
          {priority.reasoning.length > 0 && (
            <div className="flex flex-col gap-1">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide">
                Factors
              </p>
              {priority.reasoning.map((r, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs">
                  <span className="text-slate-600 shrink-0">·</span>
                  <span className="text-slate-400">{r}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
