import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { MapProperties } from "../../services/spatial";
import type { BasemapId } from "./HierarchyMap";

type MenuId = "region" | "state" | "district" | "map";

interface Props {
  states: MapProperties[];
  districts: MapProperties[];
  stateId?: string;
  districtId?: string;
  basemap: BasemapId;
  pendingReports: number;
  onRegionChange: () => void;
  onStateChange: (stateId: string) => void;
  onDistrictChange: (districtId: string) => void;
  onBasemapChange: (basemap: BasemapId) => void;
  onReportsOpen: () => void;
  onAlertsOpen: () => void;
}

const BASEMAPS: { id: BasemapId; label: string; detail: string }[] = [
  { id: "street", label: "Street", detail: "OpenStreetMap" },
  { id: "terrain", label: "Terrain", detail: "OpenTopoMap" },
  { id: "satellite", label: "Satellite", detail: "Esri imagery" },
];

function Chevron() {
  return <svg aria-hidden="true" viewBox="0 0 20 20"><path d="m5 7.5 5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.7" /></svg>;
}

function LayersIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="m12 3 9 5-9 5-9-5 9-5Zm-7.8 9L12 16.4 19.8 12M4.2 16 12 20.4 19.8 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" /></svg>;
}

export default function HierarchyCommandBar({ states, districts, stateId, districtId, basemap, pendingReports, onRegionChange, onStateChange, onDistrictChange, onBasemapChange, onReportsOpen, onAlertsOpen }: Props) {
  const [openMenu, setOpenMenu] = useState<MenuId>();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const stateName = states.find(item => item.state_id === stateId)?.state_name;
  const districtName = districts.find(item => item.district_id === districtId)?.district_name;
  const filteredDistricts = useMemo(() => districts.filter(item => item.district_name?.toLowerCase().includes(search.toLowerCase())), [districts, search]);

  useEffect(() => {
    const closeOutside = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) { setOpenMenu(undefined); setMobileOpen(false); } };
    const closeEscape = (event: KeyboardEvent) => { if (event.key === "Escape") { setOpenMenu(undefined); setMobileOpen(false); } };
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => { document.removeEventListener("mousedown", closeOutside); document.removeEventListener("keydown", closeEscape); };
  }, []);

  const toggle = (menu: MenuId) => {
    setSearch("");
    setOpenMenu(current => current === menu ? undefined : menu);
  };
  const closeMenus = () => { setOpenMenu(undefined); setMobileOpen(false); };
  const toggleMobile = () => {
    if (mobileOpen) setOpenMenu(undefined);
    setMobileOpen(open => !open);
  };

  return <div className="gis-command-bar" ref={root} aria-label="Map command bar">
    <button className="gis-mobile-command-toggle" onClick={toggleMobile} aria-expanded={mobileOpen} aria-controls="gis-command-content"><LayersIcon /><span>Controls</span></button>
    <div id="gis-command-content" className={`gis-command-content ${mobileOpen ? "open" : ""}`}>
    <div className="gis-command-selectors">
      <div className="gis-command-item">
        <button className="gis-select-button" onClick={() => toggle("region")} aria-expanded={openMenu === "region"} aria-haspopup="listbox">
          <span><small>Region</small>North-East India</span><Chevron />
        </button>
        {openMenu === "region" && <div className="gis-select-menu" role="listbox" aria-label="Regions">
          <button role="option" aria-selected onClick={() => { onRegionChange(); closeMenus(); }}>North-East India <span>NER</span></button>
        </div>}
      </div>
      <div className="gis-command-item">
        <button className="gis-select-button" onClick={() => toggle("state")} aria-expanded={openMenu === "state"} aria-haspopup="listbox">
          <span><small>State</small>{stateName ?? "Select state"}</span><Chevron />
        </button>
        {openMenu === "state" && <div className="gis-select-menu gis-select-menu-scroll" role="listbox" aria-label="States">
          {states.map(item => <button key={item.state_id} role="option" aria-selected={item.state_id === stateId} onClick={() => { onStateChange(item.state_id!); closeMenus(); }}>{item.state_name}<span>{item.state_id}</span></button>)}
        </div>}
      </div>
      <div className="gis-command-item">
        <button className="gis-select-button" disabled={!stateId} onClick={() => toggle("district")} aria-expanded={openMenu === "district"} aria-haspopup="listbox">
          <span><small>District</small>{districtName ?? "Select district"}</span><Chevron />
        </button>
        {openMenu === "district" && <div className="gis-select-menu gis-select-menu-scroll gis-district-menu" role="listbox" aria-label="Districts">
          {districts.length > 14 && <label className="gis-select-search"><span className="sr-only">Search districts</span><input autoFocus value={search} onChange={event => setSearch(event.target.value)} placeholder="Search districts…" /></label>}
          {filteredDistricts.map(item => <button key={item.district_id} role="option" aria-selected={item.district_id === districtId} onClick={() => { onDistrictChange(item.district_id!); closeMenus(); }}>{item.district_name}<span>{item.coverage_level === "DETAILED_PILOT" ? "Detailed Pilot" : "Boundary Only"}</span></button>)}
        </div>}
      </div>
    </div>

    <div className="gis-command-actions">
      <div className="gis-command-item gis-map-view-item">
        <button className="gis-toolbar-button gis-map-view-button" onClick={() => toggle("map")} aria-expanded={openMenu === "map"} aria-haspopup="dialog">
          <LayersIcon /><span>Map View</span><small>{BASEMAPS.find(item => item.id === basemap)?.label} · 2D</small>
        </button>
        {openMenu === "map" && <div className="gis-map-view-menu" role="dialog" aria-label="Map view settings">
          <p>Base map</p>
          <div className="gis-basemap-options">{BASEMAPS.map(item => <button key={item.id} className={basemap === item.id ? "active" : ""} aria-pressed={basemap === item.id} onClick={() => { onBasemapChange(item.id); closeMenus(); }}>
            <i className={`gis-basemap-preview ${item.id}`} aria-hidden="true" /><span>{item.label}<small>{item.detail}</small></span>{basemap === item.id && <b aria-label="Selected">✓</b>}
          </button>)}</div>
          <p>Display mode</p>
          <div className="gis-display-options"><button className="active" aria-pressed="true">2D <b>✓</b></button><button disabled title="Coming in Phase 4B">3D <small>Coming in Phase 4B</small></button></div>
        </div>}
      </div>
      <button className="gis-toolbar-button" onClick={onReportsOpen} aria-label="Open field reports"><span aria-hidden="true">📋</span><span className="gis-action-label">Field Reports</span>{pendingReports > 0 && <b className="gis-count">{pendingReports}</b>}</button>
      <Link className="gis-toolbar-button gis-primary-action" to="/field-report" aria-label="Create field report"><span aria-hidden="true">＋</span><span className="gis-action-label">Field Report</span></Link>
      <button className="gis-toolbar-button" onClick={onAlertsOpen} aria-label="Open alerts and notifications"><span aria-hidden="true">🔔</span><span className="gis-action-label">Alerts</span></button>
    </div>
    </div>
  </div>;
}
