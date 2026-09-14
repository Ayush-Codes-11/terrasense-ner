import { useEffect, useState } from "react";
import type { RiskRecord, WeatherContext } from "../../services/spatial";
import { riskColors, riskLabel } from "../../utils/navigation";
import { formatProvenanceLabel } from "../../utils/provenance";
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const value = (v?: number, unit = "") => typeof v === "number" && Number.isFinite(v) ? `${v.toFixed(2)}${unit}` : "Unavailable";
export default function ZoneInspector({ zone, risk, weather, loading, retrieved, onClose }: { zone: string; risk?: RiskRecord; weather?: WeatherContext; loading: boolean; retrieved?: string; onClose?: () => void }) {
  const [exposure, setExposure] = useState<any>(null);
  const [expLoading, setExpLoading] = useState(false);

  useEffect(() => {
    if (!zone || !API_BASE) return;
    let cancelled = false;
    setExpLoading(true);
    fetch(`${API_BASE}/exposure/${zone}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (!cancelled) setExposure(data); })
      .catch(() => { if (!cancelled) setExposure(null); })
      .finally(() => { if (!cancelled) setExpLoading(false); });
    return () => { cancelled = true; };
  }, [zone]);

  return <section className="gis-inspector" aria-label={`Zone ${zone} details`}>
    <div className="gis-inspector-sticky"><div><p className="gis-eyebrow">SELECTED ANALYSIS ZONE</p><h2>{zone}</h2></div>{onClose && <button className="gis-close" aria-label="Close zone details" onClick={onClose}>Close <span aria-hidden="true">×</span></button>}</div>
    <div className="gis-inspector-body">
    <span className="gis-risk-pill" style={{ borderColor: riskColors[risk?.risk_category ?? ""] }}>{riskLabel(risk?.risk_category)}</span>
    <div className="gis-score">{risk ? risk.risk_score.toFixed(4) : "-"}<small>Relative prototype risk score</small></div>
    
    {/* Exposure & Access Panel */}
    <h3>Exposure & Access</h3>
    {expLoading ? <p role="status">Calculating exposure...</p> : exposure?.summary ? (
      <dl className="gis-metrics">
        <div><dt>Facilities located within selected zone</dt><dd>{exposure.summary.critical_facilities ?? 0}</dd></div>
        <div><dt>Mapped road length within zone</dt><dd>{value(exposure.summary.total_road_km, " km")}</dd></div>
        <div><dt>Road length intersecting flagged risk area</dt><dd>Unavailable</dd></div>
        <div><dt>Road length outside flagged risk area</dt><dd>Unavailable</dd></div>
      </dl>
    ) : <p className="gis-muted">Exposure calculations temporarily unavailable.</p>}

    {loading && <p role="status">Refreshing risk.</p>}
    {!risk && !loading && <p role="status">Risk data is temporarily unavailable.</p>}
    <p className="gis-muted">Prototype Analysis Grid · Detailed Pilot</p>
    <h3>Inputs used by the scorer</h3>
    <dl className="gis-metrics">
      <div><dt>Mean slope</dt><dd>{value(risk?.slope, "°")}</dd></div>
      <div><dt>Elevation</dt><dd>{value(risk?.elevation, " m")}</dd></div>
      <div><dt>Recent 24h rainfall</dt><dd>{value(risk?.rain_24h, " mm")}</dd></div>
      <div><dt>Antecedent 3-day rainfall</dt><dd>{value(risk?.rain_3d, " mm")}</dd></div>
      <div><dt>Soil wetness · scorer input</dt><dd>{risk?.normalized_features?.soil_wetness?.toFixed(4) ?? "Unavailable"}</dd></div>
    </dl>
    <h3>Why now?</h3>
    {risk?.contributors?.length ? <ul className="gis-contributors">{risk.contributors.map((c, i) => <li key={i}><span>{c.display_name ?? c.feature}</span><strong>{c.contribution.toFixed(4)}</strong></li>)}</ul> : <p>Explanation unavailable</p>}
    <p className="gis-muted">Weighted prototype contributions, not a calibrated probability.</p>
    <h3>Forecast rainfall context</h3>
    {weather?.forecast_interval_mm ? <dl className="gis-metrics">{Object.entries(weather.forecast_interval_mm).map(([window, rain]) => <div key={window}><dt>{window.replaceAll("_", "–")} hours</dt><dd>{value(rain, " mm")}</dd></div>)}</dl> : <p>Forecast context unavailable</p>}
    {weather?.observation_timestamp && <p className="gis-muted">Observed rainfall window ends: <time>{weather.observation_timestamp}</time></p>}
    {weather?.data_meta?.note && <p className="gis-muted">{weather.data_meta.note}</p>}
    <h3>Data source & availability</h3>
    {risk?.feature_provenance ? <dl className="gis-provenance">{Object.entries(risk.feature_provenance).map(([name, source]) => <div key={name}><dt>{name.replaceAll("_", " ")}</dt><dd>{formatProvenanceLabel(source)}<span style={{ display: "none" }}>{source}</span></dd></div>)}</dl> : <p>Source information unavailable</p>}
    <p className="gis-muted">Model: prototype weighted scorer. Static ML validation pending.</p>
    {retrieved && <p className="gis-muted">API retrieved at {new Date(retrieved).toLocaleTimeString()}. Retrieval time is not observation freshness.</p>}
    </div>
  </section>;
}
