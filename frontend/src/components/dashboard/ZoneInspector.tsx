import type { RiskRecord, WeatherContext } from "../../services/spatial";
import { useZoneExposure } from "../../hooks/useZoneExposure";
import { riskColors, riskLabel } from "../../utils/navigation";
import { formatProvenanceLabel } from "../../utils/provenance";
const value = (v?: number, unit = "") => typeof v === "number" && Number.isFinite(v) ? `${v.toFixed(2)}${unit}` : "Unavailable";
export default function ZoneInspector({ zone, risk, weather, loading, retrieved, onClose }: { zone: string; risk?: RiskRecord; weather?: WeatherContext; loading: boolean; retrieved?: string; onClose?: () => void }) {
  const exposure = useZoneExposure(zone);
  const exposureData = exposure.data;

  return <section className="gis-inspector" aria-label={`Zone ${zone} details`}>
    <div className="gis-inspector-sticky"><div><p className="gis-eyebrow">SELECTED ANALYSIS ZONE</p><h2>{zone}</h2></div>{onClose && <button className="gis-close" aria-label="Close zone details" onClick={onClose}>Close <span aria-hidden="true">×</span></button>}</div>
    <div className="gis-inspector-body">
    <span className="gis-risk-pill" style={{ borderColor: riskColors[risk?.risk_category ?? ""] }}>{riskLabel(risk?.risk_category)}</span>
    <div className="gis-score">{risk ? risk.risk_score.toFixed(4) : "-"}<small>Relative prototype risk score</small></div>
    
    {/* Exposure & Access Panel */}
    <h3>Exposure & Access</h3>
    {exposure.loading ? <p role="status">Calculating mapped exposure…</p> : exposureData ? <>
      <dl className="gis-metrics">
        <div><dt>Critical facilities</dt><dd>{exposureData.summary.critical_facilities}</dd></div>
        <div><dt>Mapped communities / settlements</dt><dd>{exposureData.summary.mapped_communities}</dd></div>
        <div><dt>Motorable road length</dt><dd>{value(exposureData.summary.motorable_road_km, " km")}</dd></div>
        <div><dt>Total mapped road length</dt><dd>{value(exposureData.summary.total_road_km, " km")}</dd></div>
        {exposureData.summary.pedestrian_road_km > 0 && <div><dt>Pedestrian / path length</dt><dd>{value(exposureData.summary.pedestrian_road_km, " km")}</dd></div>}
        {exposureData.summary.track_road_km > 0 && <div><dt>Track length</dt><dd>{value(exposureData.summary.track_road_km, " km")}</dd></div>}
      </dl>
      <p className="gis-muted"><strong>Source:</strong> {exposureData.exposure_features === "REAL_OSM" ? "OpenStreetMap contributors · cached OSM snapshot" : formatProvenanceLabel(exposureData.exposure_features)}. This is not a live field observation.</p>
      {exposureData.data_meta.timestamp && <p className="gis-muted">Exposure response retrieved at <time>{new Date(exposureData.data_meta.timestamp).toLocaleString()}</time>. Retrieval time does not establish source freshness.</p>}
      <p className="gis-muted">Method: geodesic lengths of mapped OSM features clipped to the selected zone. Mapped exposure does not establish current road passability or verified blockage.</p>
    </> : <div className="gis-inline-error" role="status"><p>{exposure.error ?? "Exposure calculations are temporarily unavailable."}</p><button onClick={exposure.retry}>Retry exposure</button></div>}

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
