// ============================================================
// EmergencyPriorityCard — Prototype Decision-Support Priority
// Phase 6: 4-horizon priority evaluation holding exposure constant
//
// IMPORTANT: Always displays "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL"
// This is not a government or operational classification.
// ============================================================

import type { PriorityData, HorizonPriority } from "../../types";
import { PRIORITY_BG_CLASSES } from "../../utils/risk";
import DataSourceBadge from "../common/DataSourceBadge";

interface EmergencyPriorityCardProps {
  priority?: PriorityData | null;
  zoneId?: string | null;
}

const PRIORITY_ICONS: Record<string, string> = {
  LOW: "🟢",
  MODERATE: "🔵",
  MEDIUM: "🔵",
  HIGH: "🟠",
  VERY_HIGH: "🔴",
  CRITICAL: "🔴",
};

function HorizonRow({
  label,
  h,
}: {
  label: string;
  h?: HorizonPriority | null;
}) {
  if (!h) return null;
  const pClass = PRIORITY_BG_CLASSES[h.priority] ?? "text-slate-400";
  const icon = PRIORITY_ICONS[h.priority] ?? "⚪";

  return (
    <div className={`flex items-center justify-between px-3 py-1.5 rounded ${label === "NOW" ? 'bg-slate-800' : ''}`}>
      <span className={`w-12 text-[10px] font-mono font-medium ${label === "NOW" ? 'text-white' : 'text-slate-400'}`}>
        {label}
      </span>
      <div className="w-24 flex items-center gap-1.5">
        <span className="text-[10px]">{icon}</span>
        <span className={`text-[10px] font-bold ${pClass}`}>
          {h.priority.replace("_", " ")}
        </span>
      </div>
      <span className="w-16 text-[10px] text-slate-500 font-mono text-right tabular-nums">
        {h.priority_score.toFixed(2)}
      </span>
      <span className="w-16 text-[9px] text-slate-500 text-right truncate">
        {h.landslide_risk_category.replace("_", " ")}
      </span>
    </div>
  );
}

export default function EmergencyPriorityCard({
  priority,
  zoneId,
}: EmergencyPriorityCardProps) {
  const isPlaceholder = !priority;

  const nowH = priority?.windows?.now ?? priority?.now;
  const h24 = priority?.windows?.["24h"] ?? priority?.forecast?.["24h"];
  const h48 = priority?.windows?.["48h"] ?? priority?.forecast?.["48h"];
  const h72 = priority?.windows?.["72h"] ?? priority?.forecast?.["72h"];

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Prototype Decision-Support Priority
          </h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {zoneId ? `Zone ${zoneId} resource priority outlook` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={priority?.data_meta?.source ?? "unavailable"} />
      </div>

      {/* Strict Disclaimer — always visible */}
      <details className="group bg-slate-900/70 rounded border border-amber-900/40 open:pb-2">
        <summary className="flex items-center gap-1.5 px-2 py-1.5 cursor-pointer list-none text-[10px] text-amber-400 font-semibold select-none">
          <svg
            className="w-3.5 h-3.5 shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          ⚠ Prototype Decision Support — Not Official
          <span className="ml-auto text-slate-500 group-open:hidden">▼</span>
          <span className="ml-auto text-slate-500 hidden group-open:block">▲</span>
        </summary>
        <p className="px-2 text-[10px] text-slate-400 leading-tight mt-1 border-t border-slate-800 pt-1">
          Weights: 65% landslide risk, 20% motorable road exposure, 15% critical facilities (mapped localities retained for context). Heuristic prototype parameters, not operational emergency weights.
        </p>
      </details>

      {isPlaceholder ? (
        <div className="flex flex-col items-center justify-center py-4 gap-3">
          <div className="w-12 h-12 rounded-full bg-slate-700/60 border-2 border-dashed border-slate-600 flex items-center justify-center text-xl">
            ?
          </div>
          <p className="text-xs text-slate-500 text-center">
            Select a zone on the map to evaluate 4-horizon priority
          </p>
        </div>
      ) : (
        <>
          {/* 4-Horizon Priority Outlook Compact List */}
          <div className="flex flex-col gap-1 border border-slate-700/50 rounded bg-slate-900/30 p-1">
            <HorizonRow label="NOW" h={nowH} />
            <HorizonRow label="+24h" h={h24} />
            <HorizonRow label="+48h" h={h48} />
            <HorizonRow label="+72h" h={h72} />
          </div>

          {/* Deterministic Explanation */}
          {priority.explanation && (
            <div className="border-t border-slate-700/50 pt-2 flex flex-col gap-1 mt-1">
              <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">
                Priority Rationale
              </span>
              <p className="text-[10px] text-slate-300 leading-snug">
                {priority.explanation}
              </p>
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <p className="text-[9px] text-slate-500 border-t border-slate-700/60 pt-2 leading-tight">
        Static OSM exposure geography · Dynamic rainfall-triggered risk · Prototype Decision-Support
      </p>
    </div>
  );
}
