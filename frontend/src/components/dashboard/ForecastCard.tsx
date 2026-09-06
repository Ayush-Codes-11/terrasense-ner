// ============================================================
// ForecastCard — 24/48/72h Weather-Linked Landslide-Risk Outlook
// Phase 5: Displays computed risk scores across NOW, +24h, +48h, +72h
// using rolling 3-day antecedent rainfall accumulation.
// ============================================================

import type { ZoneForecast, RiskLevel } from "../../types";
import { RISK_BG_CLASSES, RISK_LABEL, RISK_COLORS } from "../../utils/risk";
import DataSourceBadge from "../common/DataSourceBadge";

interface ForecastCardProps {
  forecast?: ZoneForecast | null;
  zoneId?: string | null;
}

interface HorizonCellProps {
  label: string;
  risk: RiskLevel;
  score: number;
  rain3dMm?: number;
  recentMm?: number;
  intervalMm?: number | null;
  isCurrent?: boolean;
}

function HorizonCell({
  label,
  risk,
  score,
  rain3dMm,
  recentMm,
  intervalMm,
  isCurrent,
}: HorizonCellProps) {
  return (
    <div
      className={`flex flex-col items-center gap-1 p-2 rounded-lg border transition-colors ${
        isCurrent
          ? "bg-slate-800/80 border-blue-500/40 ring-1 ring-blue-500/20"
          : "bg-slate-900/60 border-slate-700/60"
      }`}
    >
      <div className="flex items-center gap-1">
        <span className="text-[10px] text-slate-400 font-semibold tracking-wide">
          {label}
        </span>
        {isCurrent && (
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
        )}
      </div>

      {/* Risk dot indicator */}
      <div
        className="w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 my-0.5"
        style={{
          backgroundColor: RISK_COLORS[risk] + "30",
          borderColor: RISK_COLORS[risk],
        }}
      >
        <div
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: RISK_COLORS[risk] }}
        />
      </div>

      <span
        className={`risk-badge text-[8px] font-bold px-1.5 py-0.5 ${RISK_BG_CLASSES[risk]}`}
      >
        {RISK_LABEL[risk]}
      </span>

      {/* Score display (never %) */}
      <span className="text-[10px] font-mono text-slate-300 font-medium mt-0.5">
        Score {score.toFixed(2)}
      </span>

      {/* Rainfall context */}
      <div className="flex flex-col items-center text-[9px] text-slate-400 border-t border-slate-700/40 w-full pt-1 mt-0.5">
        {intervalMm !== undefined && intervalMm !== null ? (
          <span className="text-blue-300 font-mono">+{intervalMm} mm</span>
        ) : recentMm !== undefined ? (
          <span className="text-slate-400 font-mono">{recentMm} mm (24h)</span>
        ) : null}
        {rain3dMm !== undefined && (
          <span className="text-[8px] text-slate-400 font-mono" title="Rolling 3-day accumulation">
            Σ3d: {rain3dMm}mm
          </span>
        )}
      </div>
    </div>
  );
}

export default function ForecastCard({ forecast, zoneId }: ForecastCardProps) {
  const isPlaceholder = !forecast;

  const nowRisk = forecast?.windows?.now?.risk ?? forecast?.now?.risk ?? forecast?.current ?? "LOW";
  const nowScore = forecast?.windows?.now?.risk_score ?? forecast?.now?.risk_score ?? forecast?.current_score ?? 0.0;
  const nowRain3d = forecast?.windows?.now?.antecedent_rain_mm ?? forecast?.now?.antecedent_rain_mm;
  const nowRecent = forecast?.windows?.now?.recent_24h_rain_mm ?? forecast?.now?.recent_24h_rain_mm;

  const h24 = forecast?.windows?.["24h"] ?? forecast?.forecast?.["24h"];
  const h48 = forecast?.windows?.["48h"] ?? forecast?.forecast?.["48h"];
  const h72 = forecast?.windows?.["72h"] ?? forecast?.forecast?.["72h"];

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Risk Outlook (24/48/72h)
          </h2>
          <p className="text-[10px] text-slate-500 mt-0.5">
            {zoneId ? `Zone ${zoneId} weather-linked risk outlook` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={forecast?.data_meta.source ?? "unavailable"} />
      </div>

      {/* Descriptive subheader */}
      <div className="text-[10px] text-slate-400 bg-slate-900/60 rounded px-2.5 py-1.5 border border-slate-700/60 flex items-center justify-between">
        <span>⚡ Sample rainfall scenario → computed risk outlook</span>
        <span className="text-[9px] text-slate-400 font-mono">Rolling 3-day window</span>
      </div>

      {isPlaceholder ? (
        <div className="flex flex-col gap-2">
          {/* Skeleton windows */}
          <div className="grid grid-cols-4 gap-2">
            {["NOW", "+24h", "+48h", "+72h"].map((w) => (
              <div
                key={w}
                className="flex flex-col items-center gap-1.5 p-2 rounded-lg bg-slate-900/30 border border-dashed border-slate-700/50"
              >
                <span className="text-[10px] text-slate-600">{w}</span>
                <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700" />
                <div className="w-12 h-3 rounded bg-slate-800" />
                <div className="w-10 h-2.5 rounded bg-slate-800/60 mt-1" />
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 text-center">
            Click a zone to evaluate 24/48/72h outlook
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {/* 4-Horizon Grid */}
          <div className="grid grid-cols-4 gap-2">
            <HorizonCell
              label="NOW"
              risk={nowRisk}
              score={nowScore}
              rain3dMm={nowRain3d}
              recentMm={nowRecent}
              isCurrent
            />
            {h24 && (
              <HorizonCell
                label="+24h"
                risk={h24.risk}
                score={h24.risk_score}
                rain3dMm={h24.antecedent_rain_mm}
                recentMm={h24.recent_24h_rain_mm}
                intervalMm={h24.forecast_interval_rain_mm}
              />
            )}
            {h48 && (
              <HorizonCell
                label="+48h"
                risk={h48.risk}
                score={h48.risk_score}
                rain3dMm={h48.antecedent_rain_mm}
                recentMm={h48.recent_24h_rain_mm}
                intervalMm={h48.forecast_interval_rain_mm}
              />
            )}
            {h72 && (
              <HorizonCell
                label="+72h"
                risk={h72.risk}
                score={h72.risk_score}
                rain3dMm={h72.antecedent_rain_mm}
                recentMm={h72.recent_24h_rain_mm}
                intervalMm={h72.forecast_interval_rain_mm}
              />
            )}
          </div>

          {/* Deterministic Explanation: Why risk changes */}
          {forecast.risk_change_summary && (
            <div className="bg-slate-900/70 border border-slate-700/60 rounded-md p-2 flex flex-col gap-1">
              <span className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">
                Why risk changes
              </span>
              <p className="text-[10px] text-slate-300 leading-snug">
                {forecast.risk_change_summary}
              </p>
              {forecast.transition_details && forecast.transition_details.length > 0 && (
                <ul className="text-[9px] text-slate-400 list-disc list-inside space-y-0.5 mt-0.5">
                  {forecast.transition_details.map((d, i) => (
                    <li key={i} className="leading-tight">
                      {d}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {forecast && (
        <p className="text-[9px] text-slate-400 border-t border-slate-700 pt-2 leading-tight">
          Prototype scoring engine · All horizons computed dynamically · Rainfall inputs are SAMPLE_MOCK (not a live IMD forecast)
        </p>
      )}
    </div>
  );
}
