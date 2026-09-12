import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import HierarchyMap from "../components/map/HierarchyMap";
import ZoneInspector from "../components/dashboard/ZoneInspector";
import { useHierarchyMap } from "../hooks/useHierarchyMap";
import { usePilotRisk } from "../hooks/usePilotRisk";
import { clearSpatialCache } from "../services/spatial";
import type { Boundaries } from "../services/spatial";
import { readSelection, selectLevel, riskColors, riskLabel } from "../utils/navigation";
import "./gis.css";
const empty: Boundaries = { type: "FeatureCollection", features: [] };
export default function Dashboard() {
  const [params, setParams] = useSearchParams();
  const selection = readSelection(params);
  const [retry, setRetry] = useState(0);
  const [gridFocus, setGridFocus] = useState(false);
  const hierarchy = useHierarchyMap(selection, retry);
  const data = hierarchy.data;
  const pilot = Boolean(data?.detailed);
  const risk = usePilotRisk(pilot, selection.zone);
  const navigate = (level: "region" | "state" | "district" | "zone", id?: string) => {
    const next = selectLevel(selection, level, id);
    setParams(Object.fromEntries(Object.entries(next).filter((entry): entry is [string, string] => Boolean(entry[1]))));
    setGridFocus(false);
  };
  const level = pilot ? "zone" : data?.state ? "district" : "state";
  const features = pilot ? data?.zones ?? empty : data?.district ? { ...data.districts!, features: data.districts!.features.filter(f => f.properties.district_id === selection.district) } : data?.districts ?? data?.states ?? empty;
  const focus = useMemo((): Boundaries => {
    if (!data) return empty;
    if (selection.zone && data.zones) return { ...data.zones, features: data.zones.features.filter(f => f.properties.zone_id === selection.zone) };
    if (gridFocus && data.zones) return data.zones;
    if (data.district) return { ...data.districts!, features: data.districts!.features.filter(f => f.properties.district_id === data.district!.district_id) };
    if (data.state) return { ...data.states, features: data.states.features.filter(f => f.properties.state_id === data.state!.state_id) };
    return data.states;
  }, [data, selection.zone, gridFocus]);
  const context = useMemo(() => data?.district && data.districts ? { ...data.districts, features: data.districts.features.filter(f => f.properties.district_id === data.district!.district_id) } : undefined, [data]);
  const title = selection.zone ?? data?.district?.district_name ?? data?.state?.state_name ?? "North-East India";
  return <div className="gis-shell">
    <header className="gis-header"><a href="/" className="gis-brand"><span aria-hidden="true">◈</span><div>TerraSense<small>NER · GEOSPATIAL COMMAND CENTRE</small></div></a><span className="gis-header-tag">2D · Research prototype</span></header>
    <nav className="gis-breadcrumb" aria-label="Geographic breadcrumb">
      <button onClick={() => navigate("region")}>North-East India</button>
      {data?.state && <><span aria-hidden="true">/</span><button onClick={() => navigate("state", data.state!.state_id)}>{data.state.state_name}</button></>}
      {data?.district && <><span aria-hidden="true">/</span><button onClick={() => navigate("district", data.district!.district_id)}>{data.district.district_name}</button></>}
      {selection.zone && <><span aria-hidden="true">/</span><span aria-current="location">{selection.zone}</span></>}
    </nav>
    <main className={`gis-workspace ${selection.zone ? "has-inspector" : ""}`}>
      <aside className="gis-navigation" aria-label="Geographic navigation">
        <p className="gis-eyebrow">SPATIAL EXPLORER</p><h1>{title}</h1>
        <p className="gis-muted">Explore boundaries. Inspect the detailed pilot.</p>
        {hierarchy.loading && <p role="status">Loading spatial data…</p>}
        {hierarchy.error && <div role="alert"><p>{hierarchy.error}</p><button className="gis-action" onClick={() => { clearSpatialCache(); setRetry(r => r + 1); }}>Retry</button><button className="gis-action" onClick={() => navigate("region")}>Return to North-East India</button></div>}
        {data && <>
          <div className="gis-summary"><strong>{pilot ? data.zones?.features.length : data.district ? "Boundary Only" : data.districts?.features.length ?? data.states.features.length}</strong><span>{pilot ? "Prototype Analysis Grid zones" : data.district ? "Detailed model not implemented" : data.state ? "prototype-boundary districts" : "states · NER coverage"}</span></div>
          {!data.district && <p className="gis-notice">Detailed risk model not yet available at {data.state ? "state" : "regional"} level.</p>}
          {data.district && <div className="gis-notice"><strong>{pilot ? "Detailed Pilot" : "Boundary Only"}</strong><p>Boundary available</p><p>{pilot ? "Relative prototype risk available. Static ML validation pending." : "Detailed model not implemented"}</p><small>{data.district.risk_model_status}</small></div>}
          {pilot && <button className="gis-action" onClick={() => setGridFocus(true)}>Fit 25-zone pilot grid</button>}
          <h2 className="gis-list-heading">{pilot ? "Select an analysis zone" : data.state ? "Districts" : "Select a state"}</h2>
          <div className="gis-feature-list">{(pilot ? data.zones?.features : data.districts?.features ?? data.states.features)?.map(feature => {
            const id = feature.properties[`${level}_id`]!;
            const name = feature.properties[`${level}_name` as "state_name" | "district_name"] ?? id;
            const band = risk.risks.find(r => r.zone_id === id)?.risk_category;
            return <button key={id} aria-pressed={id === (selection.zone ?? selection.district ?? selection.state)} onClick={() => navigate(level, id)}><span>{name}</span>{level === "zone" ? <small style={{ color: riskColors[band ?? ""] }}>{riskLabel(band)}</small> : <span aria-hidden="true">↗</span>}</button>;
          })}</div>
          {pilot && !data.zones?.features.length && <p>No analysis zones available.</p>}
        </>}
        <footer className="gis-vintage">Boundary reference<br/><strong>ADM1 2011 · ADM2 2021</strong><p>Committed prototype dataset; not a definitive current administrative list.</p></footer>
      </aside>
      <section className="gis-map-stage" aria-label="Spatial view">
        {data ? <HierarchyMap data={features} focus={focus} context={pilot ? context : undefined} level={level} selected={selection.zone ?? selection.district} risks={risk.risks} onSelect={id => navigate(level, id)} /> : <div className="gis-map-empty">{hierarchy.loading ? "Preparing North-East India…" : "Spatial data unavailable"}</div>}
        <div className="gis-map-caption"><span>{pilot ? "AIZAWL · DETAILED PILOT" : "ADMINISTRATIVE BOUNDARIES"}</span><strong>{pilot ? "Relative Risk" : "Boundary coverage"}</strong></div>
        {pilot && <div className="gis-legend" aria-label="Relative risk legend">{Object.entries(riskColors).map(([band, color]) => <span key={band}><i style={{ background: color }} />{riskLabel(band)}</span>)}<span><i style={{ background: "#8b98a6" }} />Unavailable</span></div>}
        {pilot && risk.error && <div className="gis-risk-error" role="status">Risk data unavailable. Boundaries remain visible.</div>}
      </section>
      {selection.zone && <aside className="gis-detail"><button className="gis-close" aria-label="Close zone details" onClick={() => navigate("district", selection.district)}>Close ×</button><ZoneInspector zone={selection.zone} risk={risk.risks.find(r => r.zone_id === selection.zone)} weather={risk.weather} loading={risk.loading} retrieved={risk.retrieved} /></aside>}
    </main>
  </div>;
}
