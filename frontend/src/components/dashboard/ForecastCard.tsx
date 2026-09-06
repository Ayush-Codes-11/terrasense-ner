// ============================================================
// ForecastCard — 24/48/72h Weather-Linked Landslide-Risk Outlook
// Phase 5: Displays computed risk scores across NOW, +24h, +48h, +72h
// using rolling 3-day antecedent rainfall accumulation.
// ============================================================

import type { ZoneForecast, RiskLevel } from "../../types";
import { RISK_LABEL, RISK_COLORS } from "../../utils/risk";
import DataSourceBadge from "../common/DataSourceBadge";

interface ForecastCardProps {
  forecast?: ZoneForecast | null;
  zoneId?: string | null;
}

function HorizonRow({
  label,
  risk,
  score,
  intervalMm,
  isCurrent,
}: { label: string; risk: RiskLevel; score: number; intervalMm?: number | null; isCurrent?: boolean }) {
  return (
    <div className={`flex items-center justify-between px-3 py-1.5 rounded ${isCurrent ? 'bg-slate-800' : ''}`}>
      <span className={`w-12 text-[10px] font-mono font-medium ${isCurrent ? 'text-white' : 'text-slate-400'}`}>
        {label}
      </span>
      <span className={`w-24 text-[10px] font-bold ${RISK_COLORS[risk] === '#ef4444' ? 'text-red-400' : RISK_COLORS[risk] === '#f97316' ? 'text-orange-400' : RISK_COLORS[risk] === '#eab308' ? 'text-yellow-400' : 'text-green-400'}`}>
        {RISK_LABEL[risk]}
      </span>
      <span className="w-16 text-[10px] text-slate-500 font-mono text-right tabular-nums">
        {score.toFixed(2)}
      </span>
      {intervalMm !== undefined && intervalMm !== null && (
        <span className="w-16 text-[9px] text-blue-400 text-right tabular-nums">+{intervalMm}mm</span>
      )}
    </div>
  );
}

export default function ForecastCard({ forecast, zoneId }: ForecastCardProps) {
  const isPlaceholder = !forecast;

  const nowRisk = forecast?.windows?.now?.risk ?? forecast?.now?.risk ?? forecast?.current ?? "LOW";
  const nowScore = forecast?.windows?.now?.risk_score ?? forecast?.now?.risk_score ?? forecast?.current_score ?? 0.0;

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
          {/* 4-Horizon Compact List */}
          <div className="flex flex-col gap-1 border border-slate-700/50 rounded bg-slate-900/30 p-1">
            <HorizonRow label="NOW" risk={nowRisk} score={nowScore} isCurrent />
            {h24 && <HorizonRow label="+24h" risk={h24.risk} score={h24.risk_score} intervalMm={h24.forecast_interval_rain_mm} />}
            {h48 && <HorizonRow label="+48h" risk={h48.risk} score={h48.risk_score} intervalMm={h48.forecast_interval_rain_mm} />}
            {h72 && <HorizonRow label="+72h" risk={h72.risk} score={h72.risk_score} intervalMm={h72.forecast_interval_rain_mm} />}
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
