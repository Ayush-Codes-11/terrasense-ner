import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import AlertsPanel from "../components/dashboard/AlertsPanel";
import ZoneInspector from "../components/dashboard/ZoneInspector";
import HierarchyCommandBar from "../components/map/HierarchyCommandBar";
import HierarchyMap from "../components/map/HierarchyMap";
import type { BasemapId } from "../components/map/HierarchyMap";
import ReportList from "../components/reports/ReportList";
import SideDrawer from "../components/ui/SideDrawer";
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
  const [basemap, setBasemap] = useState<BasemapId>("terrain");
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isReportsOpen, setIsReportsOpen] = useState(false);
  const [isDataStatusOpen, setIsDataStatusOpen] = useState(false);
  const [localReports, setLocalReports] = useState<any[]>([]);
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const hierarchy = useHierarchyMap(selection, retry);
  const data = hierarchy.data;
  const pilot = Boolean(data?.detailed);
  const risk = usePilotRisk(pilot, selection.zone);

  useEffect(() => {
    const update = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);

  useEffect(() => {
    let active = true;
    import("../services/db").then(({ getLocalReports, syncPendingReports }) => {
      if (navigator.onLine) void syncPendingReports().catch(() => undefined);
      return getLocalReports();
    }).then(reports => { if (active) setLocalReports(reports ?? []); }).catch(() => undefined);
    return () => { active = false; };
  }, []);

  const navigate = (level: "region" | "state" | "district" | "zone", id?: string) => {
    const next = selectLevel(selection, level, id);
    setParams(Object.fromEntries(Object.entries(next).filter((entry): entry is [string, string] => Boolean(entry[1]))));
    setGridFocus(false);
  };
  const level = pilot ? "zone" : data?.state ? "district" : "state";
  const features = pilot
    ? data?.zones ?? empty
    : data?.district
      ? { ...data.districts!, features: data.districts!.features.filter(feature => feature.properties.district_id === selection.district) }
      : data?.districts ?? data?.states ?? empty;
  const focus = useMemo((): Boundaries => {
    if (!data) return empty;
    if (gridFocus && data.zones) return data.zones;
    if (selection.zone && data.zones) return { ...data.zones, features: data.zones.features.filter(feature => feature.properties.zone_id === selection.zone) };
    if (data.zones) return data.zones;
    if (data.district) return { ...data.districts!, features: data.districts!.features.filter(feature => feature.properties.district_id === data.district!.district_id) };
    if (data.state) return { ...data.states, features: data.states.features.filter(feature => feature.properties.state_id === data.state!.state_id) };
    return data.states;
  }, [data, selection.zone, gridFocus]);
  const context = useMemo(() => data?.district && data.districts
    ? { ...data.districts, features: data.districts.features.filter(feature => feature.properties.district_id === data.district!.district_id) }
    : undefined, [data]);
  const title = data?.district?.district_name ?? data?.state?.state_name ?? "North-East India";
  const pendingReports = localReports.filter(report => report.sync_status !== "SYNCED").length;
  const states = data?.states.features.map(feature => feature.properties) ?? [];
  const districts = data?.districts?.features.map(feature => feature.properties) ?? [];
  const count = pilot ? data?.zones?.features.length : data?.district ? 1 : data?.districts?.features.length ?? data?.states.features.length;
  const selectedRisk = risk.risks.find(item => item.zone_id === selection.zone);

  return <div className="gis-shell">
    <header className="gis-header">
      <a href="/" className="gis-brand" aria-label="TerraSense command centre home"><span aria-hidden="true">◈</span><div>TerraSense NER<small>LANDSLIDE DECISION SUPPORT · RESEARCH PROTOTYPE</small></div></a>
      <HierarchyCommandBar states={states} districts={districts} stateId={selection.state} districtId={selection.district} basemap={basemap} pendingReports={pendingReports}
        onRegionChange={() => navigate("region")} onStateChange={id => navigate("state", id)} onDistrictChange={id => navigate("district", id)} onBasemapChange={setBasemap}
        onReportsOpen={() => setIsReportsOpen(true)} onAlertsOpen={() => setIsAlertsOpen(true)} />
    </header>
    <main className="gis-workspace">
      <section className="gis-map-stage" aria-label="Spatial view">
        {data ? <HierarchyMap data={features} focus={focus} context={pilot ? context : undefined} level={level} selected={selection.zone ?? selection.district} risks={risk.risks} basemap={basemap} onSelect={id => navigate(level, id)} />
          : <div className="gis-map-empty">{hierarchy.loading ? "Preparing North-East India…" : "Spatial data unavailable"}</div>}

        <div className="gis-context-hud">
          <nav className="gis-breadcrumb" aria-label="Geographic breadcrumb">
            <button onClick={() => navigate("region")}>North-East India</button>
            {data?.state && <><span aria-hidden="true">›</span><button onClick={() => navigate("state", data.state!.state_id)}>{data.state.state_name}</button></>}
            {data?.district && <><span aria-hidden="true">›</span><button onClick={() => navigate("district", data.district!.district_id)}>{data.district.district_name}</button></>}
            {selection.zone && <><span aria-hidden="true">›</span><span aria-current="location">{selection.zone}</span></>}
          </nav>
          <p className="gis-eyebrow">{pilot ? "AIZAWL · DETAILED PILOT" : "ADMINISTRATIVE BOUNDARIES"}</p>
          <div className="gis-context-heading"><h1>{title}</h1><strong>{count ?? "—"}</strong></div>
          <p className="gis-context-copy">{pilot ? "Prototype Analysis Grid zones · relative risk available" : data?.district ? "Boundary available · detailed model not implemented" : data?.state ? "Prototype-boundary districts · detailed state risk not available" : "States in the North-East India hierarchy"}</p>
          {data?.district && <span className={`gis-coverage-pill ${pilot ? "pilot" : "boundary"}`}>{pilot ? "Detailed Pilot" : "Boundary Only"}</span>}
          {pilot && <button className="gis-fit-action" onClick={() => setGridFocus(true)}>Fit all 25 zones</button>}
          {hierarchy.error && <div className="gis-error" role="alert"><p>{hierarchy.error}</p><button onClick={() => { clearSpatialCache(); setRetry(value => value + 1); }}>Retry</button><button onClick={() => navigate("region")}>Return to NER</button></div>}
        </div>

        {pilot && <div className="gis-legend" aria-label="Relative risk legend"><strong>Relative Risk</strong>{Object.entries(riskColors).map(([band, color]) => <span key={band}><i style={{ background: color }} />{riskLabel(band)}</span>)}<span><i style={{ background: "#8b98a6" }} />Unavailable</span></div>}
        {pilot && risk.error && <div className="gis-risk-error" role="status">Risk data unavailable. Boundaries remain visible.</div>}
        <div className="gis-vintage">ADM1 2011 · ADM2 2021 prototype boundaries</div>

        <div className={`gis-data-status ${selection.zone ? "with-inspector" : ""}`}>
          <button aria-expanded={isDataStatusOpen} onClick={() => setIsDataStatusOpen(open => !open)}><i className={data ? "available" : "unavailable"} />Data Status</button>
          {isDataStatusOpen && <div className="gis-data-status-popover">
            <strong>Data sources & availability</strong>
            <dl><div><dt>Hierarchy</dt><dd>{data ? "Available" : "Unavailable"}</dd></div><div><dt>Basemap</dt><dd>{basemap === "terrain" ? "OpenTopoMap" : basemap === "street" ? "OpenStreetMap" : "Esri imagery"}</dd></div><div><dt>Detailed model</dt><dd>{pilot ? "Aizawl pilot" : "Not available at this level"}</dd></div>{selectedRisk?.feature_provenance && Object.entries(selectedRisk.feature_provenance).map(([name, source]) => <div key={name}><dt>{name.replaceAll("_", " ")}</dt><dd>{source}</dd></div>)}</dl>
            <small>Availability and provenance are not model confidence.</small>
          </div>}
        </div>

        {selection.zone && <aside className="gis-detail" aria-label="Selected zone inspector" onWheel={event => event.stopPropagation()}><ZoneInspector zone={selection.zone} risk={selectedRisk} weather={risk.weather} loading={risk.loading} retrieved={risk.retrieved} onClose={() => navigate("district", selection.district)} /></aside>}
      </section>
    </main>

    <SideDrawer isOpen={isAlertsOpen} onClose={() => setIsAlertsOpen(false)} title="Active Alerts"><AlertsPanel /></SideDrawer>
    <SideDrawer isOpen={isReportsOpen} onClose={() => setIsReportsOpen(false)} title="Field Reports">
      <div className="gis-drawer-status"><span className={isOnline ? "online" : "offline"}><i />{isOnline ? "Online" : "Offline"}</span><a href="/field-report">+ New Report</a></div>
      <ReportList reports={localReports} />
    </SideDrawer>
  </div>;
}
