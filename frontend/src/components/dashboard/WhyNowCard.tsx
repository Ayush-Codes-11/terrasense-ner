// ============================================================
// WhyNowCard — prototype feature attribution
// Phase 1: placeholder
// Phase 7+: receives WhyNowData from /why-now/{zone_id}
//
// RULE: No fabricated percentages or SHAP values.
// Values shown only when real data or prototype scorer provides them.
// ============================================================

import type { WhyNowData, FeatureDirection } from "../../types";
import DataSourceBadge from "../common/DataSourceBadge";

interface WhyNowCardProps {
  whyNow?: WhyNowData | null;
  zoneId?: string | null;
}

const DIRECTION_ICON: Record<FeatureDirection, string> = {
  up: "↑",
  down: "↓",
  neutral: "→",
};

const DIRECTION_COLOR: Record<FeatureDirection, string> = {
  up: "text-red-400",
  down: "text-green-400",
  neutral: "text-slate-400",
};

const FRESHNESS_CLASSES: Record<string, string> = {
  "REAL DEM": "bg-green-500/10 text-green-400 border-green-500/30",
  "REAL GPM": "bg-green-500/10 text-green-400 border-green-500/30",
  "SAMPLE GPM": "bg-amber-500/10 text-amber-400 border-amber-500/30",
  REAL: "bg-green-500/10 text-green-400 border-green-500/30",
  Real: "bg-green-500/10 text-green-400 border-green-500/30",
  Sample: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  Static: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  Unavailable: "bg-slate-700/10 text-slate-600 border-slate-700/30",
};

export default function WhyNowCard({ whyNow, zoneId }: WhyNowCardProps) {
  const isPlaceholder = !whyNow;
  const modelLabel =
    whyNow?.model_type === "xgboost"
      ? "XGBoost + SHAP"
      : whyNow?.model_type === "prototype"
        ? "Prototype Weighted Scorer"
        : "Sample Scenario Drivers";

  const modelFooter =
    whyNow?.model_type === "xgboost"
      ? "SHAP value attribution from XGBoost model. No accuracy claims are made."
      : whyNow?.model_type === "prototype"
        ? "Transparent prototype feature contributions. Not a calibrated probability model."
        : "Illustrative drivers from SAMPLE_MOCK scenario data. Risk engine connected in Phase 4.";

  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
            Why Now?
          </h2>
          <p className="text-[10px] text-slate-600 mt-0.5">
            {zoneId ? `Zone ${zoneId} risk drivers` : "Select a zone on the map"}
          </p>
        </div>
        <DataSourceBadge source={whyNow?.data_meta.source ?? "unavailable"} />
      </div>

      {isPlaceholder ? (
        <div className="flex flex-col gap-2">
          {/* Placeholder driver rows */}
          {[
            "3-day rainfall accumulation",
            "24h forecast rainfall",
            "Terrain slope contribution",
            "Soil moisture index",
          ].map((label) => (
            <div
              key={label}
              className="flex items-center justify-between py-1.5 border-b border-slate-700/30 last:border-0"
            >
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-slate-700 border border-dashed border-slate-600" />
                <span className="text-xs text-slate-600">{label}</span>
              </div>
              <div className="w-12 h-3 bg-slate-800 rounded" />
            </div>
          ))}
          <p className="text-[10px] text-slate-600 text-center pt-1">
            Click a zone to see feature drivers
          </p>
        </div>
      ) : (
        <>
          {/* Model type tag */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-slate-500">Source:</span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded border ${
                whyNow.model_type === "sample"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  : "bg-blue-500/10 text-blue-400 border-blue-500/30"
              }`}
            >
              {modelLabel}
            </span>
          </div>

          {/* Driver rows */}
          <div className="flex flex-col gap-0.5">
            {whyNow.drivers.map((d, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-2 border-b border-slate-700/30 last:border-0"
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span
                    className={`text-base font-bold shrink-0 ${DIRECTION_COLOR[d.direction]}`}
                  >
                    {DIRECTION_ICON[d.direction]}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs text-slate-300 font-medium truncate">
                      {d.display_name}
                    </p>
                    <p className="text-[10px] text-slate-500 truncate">
                      {d.description}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                  {d.contribution !== undefined && (
                    <span className="text-[10px] font-mono text-slate-300 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded">
                      +{d.contribution.toFixed(4)}
                    </span>
                  )}
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded border ${
                      FRESHNESS_CLASSES[d.freshness] ?? FRESHNESS_CLASSES.Unavailable
                    }`}
                  >
                    {d.freshness}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <p className="text-[10px] text-slate-600 border-t border-slate-700 pt-2">
            {modelFooter}
          </p>
        </>
      )}
    </div>
  );
}
