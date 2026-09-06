// ============================================================
// ForecastCard — 24/48/72h antecedent-rainfall-aware risk outlook
// Phase 1: shows placeholder state
// Phase 4+: receives ZoneForecast from /risk/forecast/{zone_id}
// ============================================================

import type { ZoneForecast, RiskLevel } from "../../types";
import { RISK_BG_CLASSES, RISK_LABEL, RISK_COLORS } from "../../utils/risk";
import DataSourceBadge from "../common/DataSourceBadge";

interface ForecastCardProps {
  forecast?: ZoneForecast | null;
  zoneId?: string | null;
}

const WINDOWS = ["NOW", "+24h", "+48h", "+72h"] as const;

function WindowCell({
  label,
  risk,
  rainMm,
  isCurrent,
}: {
  label: string;
  risk: RiskLevel;
  rainMm?: number;
  isCurrent?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center gap-1 p-2 rounded-lg border transition-colors ${
        isCurrent
          ? "bg-slate-700/60 border-slate-600"
          : "bg-slate-900/40 border-slate-700/50"
      }`}
    >
      <span className="text-[10px] text-slate-500 font-medium">{label}</span>
      {/* Risk dot */}
      <div
        className="w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0"
        style={{
          backgroundColor: RISK_COLORS[risk] + "30",
          borderColor: RISK_COLORS[risk],
        }}
      >
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: RISK_COLORS[risk] }}
        />
      </div>
      <span
        className={`risk-badge text-[9px] px-1.5 py-0.5 ${RISK_BG_CLASSES[risk]}`}
      >
        {RISK_LABEL[risk]}
      </span>
      {rainMm !== undefined && (
        <span className="text-[10px] text-slate-500">{rainMm} mm</span>
      )}
    </div>
  );
}

export default function ForecastCard({ forecast, zoneId }: ForecastCardProps) {
  const isPlaceholder = !forecast;

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Risk Outlook
          </h2>
          <p className="text-[10px] text-slate-600 mt-0.5">
            {zoneId ? `Zone ${zoneId}` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={forecast?.data_meta.source ?? "unavailable"} />
      </div>

      {/* Antecedent rainfall note */}
      <div className="text-[10px] text-slate-500 bg-slate-900/50 rounded px-2 py-1 border border-slate-700/50">
        ⚡ Outlook accounts for accumulated (antecedent) rainfall — each window
        adds to prior observed rain.
      </div>

      {isPlaceholder ? (
        <div className="flex flex-col gap-2">
          {/* Skeleton windows */}
          <div className="grid grid-cols-4 gap-2">
            {WINDOWS.map((w) => (
              <div
                key={w}
                className="flex flex-col items-center gap-1.5 p-2 rounded-lg bg-slate-900/30 border border-dashed border-slate-700/50"
              >
                <span className="text-[10px] text-slate-600">{w}</span>
                <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700" />
                <div className="w-12 h-3 rounded bg-slate-800" />
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 text-center">
            Click a zone to see 24/48/72h forecast
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-2">
          <WindowCell
            label="NOW"
            risk={forecast.current}
            isCurrent
          />
          <WindowCell
            label="+24h"
            risk={forecast.forecast["24h"].risk}
            rainMm={forecast.forecast["24h"].antecedent_rain_mm}
          />
          <WindowCell
            label="+48h"
            risk={forecast.forecast["48h"].risk}
            rainMm={forecast.forecast["48h"].antecedent_rain_mm}
          />
          <WindowCell
            label="+72h"
            risk={forecast.forecast["72h"].risk}
            rainMm={forecast.forecast["72h"].antecedent_rain_mm}
          />
        </div>
      )}

      {forecast && (
        <p className="text-[10px] text-slate-600 border-t border-slate-700 pt-2">
          Prototype scoring model · rainfall totals are accumulated across windows
        </p>
      )}
    </div>
  );
}
