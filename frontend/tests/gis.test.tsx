import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { readFileSync } from "node:fs";
import Dashboard from "../src/pages/Dashboard";
import ZoneInspector from "../src/components/dashboard/ZoneInspector";
import { AIZAWL, pilotZones, riskLabel, selectLevel } from "../src/utils/navigation";
import { clearSpatialCache, spatialFetch } from "../src/services/spatial";

vi.mock("../src/components/map/HierarchyMap", () => ({ default: ({ data, focus, level, onSelect }: any) => <div data-testid="map" data-focus-count={focus.features.length}>{level}: {data.features.length} features{data.features.map((feature: any) => {
  const id = feature.properties[`${level}_id`];
  return <button key={id} onClick={() => onSelect(id)}>{feature.properties[`${level}_name`] ?? id}</button>;
})}</div> }));
vi.mock("../src/components/map/TerrainMap3D", () => ({ default: ({ data, selected, basemap, onSelect, onFailure }: any) => <div data-testid="terrain-map" data-basemap={basemap} data-selected={selected}>3D: {data.features.length} features<button onClick={() => onSelect("C03")}>Select C03 in 3D</button><button onClick={() => onFailure("Aizawl terrain tiles are unavailable. The map has returned to 2D.")}>Fail terrain</button></div> }));
const read = (path: string) => JSON.parse(readFileSync(new URL(path, import.meta.url), "utf8"));
const states = read("../../data/geodata/ner/states.geojson");
const districts = read("../../data/geodata/ner/districts.geojson");
districts.features.forEach((f: any) => {
  const pilot = f.properties.district_id === AIZAWL;
  f.properties.coverage_level = pilot ? "DETAILED_PILOT" : "DISTRICT_BOUNDARY_ONLY";
  f.properties.risk_model_status = pilot ? "STATIC_ML_VALIDATION_PENDING" : "NOT_IMPLEMENTED";
});
const grid = read("../../data/sample/grid-risk.geojson");
const info = { count: 25, detailed_zone_model_available: true, items: grid.features.map((f: any) => ({ zone_id: f.properties.zone_id, district_id: AIZAWL, zone_type: "PROTOTYPE_ANALYSIS_GRID" })) };
const risk = { zone_id: "C03", risk_category: "HIGH", risk_score: .7103, slope: 22.01, rain_24h: 51.85, rain_3d: 105.69,
  soil_moisture: .62, soil_wetness_index: .62, normalized_features: { soil_wetness: .9276 },
  contributors: [{ feature: "Soil wetness index", contribution: .1391 }], feature_provenance: { soil_wetness: "REAL_SOIL_MOISTURE", slope: "REAL_DEM", rainfall: "REAL_GPM", forecast_rainfall: "REAL_FORECAST" } };
const osmMeta = { data_type: "REAL_OSM", source: "OpenStreetMap contributors via Overpass API", is_live: false, attribution: "© OpenStreetMap contributors" };
const facilities = { type: "FeatureCollection", data_meta: osmMeta, features: [
  { type: "Feature", properties: { facility_id: "h1", name: "Civil Hospital", category: "hospital", source: "OpenStreetMap contributors" }, geometry: { type: "Point", coordinates: [92.72, 23.73] } },
  { type: "Feature", properties: { facility_id: "c1", name: null, category: "clinic", source: "OpenStreetMap contributors" }, geometry: { type: "Point", coordinates: [92.71, 23.72] } },
  { type: "Feature", properties: { facility_id: "p1", name: "Central Police", category: "police", source: "OpenStreetMap contributors" }, geometry: { type: "Point", coordinates: [92.73, 23.74] } },
] };
const roads = { type: "FeatureCollection", data_meta: osmMeta, features: [
  { type: "Feature", properties: { osm_id: "r1", highway: "primary" }, geometry: { type: "LineString", coordinates: [[92.7, 23.7], [92.73, 23.74]] } },
] };
const exposure = { zone_id: "C03", summary: { osm_road_segments_count: 277, motorable_road_segments_count: 241, motorable_road_km: 49.85, total_road_km: 52.092, pedestrian_road_km: 2.242, track_road_km: 0, mapped_communities: 1, critical_facilities: 5, roads_blocked: 0, roads_exposed: 277, roads_exposed_km: 49.85, villages_exposed: 1, hospitals_exposed: 5 }, roads: [], settlements: [], critical_facilities: [], hazard_geometry: "SAMPLE_MOCK", exposure_features: "REAL_OSM", analysis_mode: "PROTOTYPE_MIXED_PROVENANCE", data_meta: { ...osmMeta, timestamp: "2026-09-23T10:00:00Z" } };
function response(body: unknown, status = 200) { return Promise.resolve({ ok: status === 200, status, json: async () => body } as Response); }
function mount(search = "") { return render(<MemoryRouter initialEntries={["/" + search]}><Dashboard /></MemoryRouter>); }
beforeEach(() => {
  clearSpatialCache();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(((kind: string) => kind === "webgl2" ? {} : null) as any);
  vi.stubGlobal("fetch", vi.fn((url: string) => {
    if (url.includes("/regions/NER/states")) return response(states);
    if (url.includes("/states/")) return response({ ...districts, features: districts.features.filter((f: any) => url.includes(f.properties.state_id)) });
    if (url.includes("/districts/")) return response(url.includes(AIZAWL) ? info : { count: 0, items: [], detailed_zone_model_available: false });
    if (url.endsWith("/zones")) return response(grid);
    if (url.includes("/risk/current")) return response({ zones: [risk] });
    if (url.includes("/weather/")) return response({ forecast_interval_mm: { "0_24h": 10.9 }, observation_timestamp: "2026-09-08T23:59:59Z" });
    if (url.includes("/exposure/")) return response({ ...exposure, zone_id: url.split("/").pop() });
    if (url.includes("/geodata/osm/critical-facilities")) return response(facilities);
    if (url.includes("/geodata/osm/roads")) return response(roads);
    if (url.includes("/geodata/osm/status")) return response({ status: "OSM snapshot", is_real: true, retrieved_at: "2026-09-06T08:02:54Z", source: osmMeta.source, attribution: osmMeta.attribution, feature_counts: { roads: 1485, critical_facilities: 31, whitelisted_critical_facilities: 20 }, data_meta: osmMeta });
    return response({}, 404);
  }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("GIS command centre", () => {
  it("starts at eight states and navigates to 11 Mizoram districts", async () => {
    mount();
    expect(await screen.findByText("state: 8 features")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /State.*Select state/ }));
    await userEvent.click(screen.getByRole("option", { name: /Mizoram/ }));
    expect(await screen.findByText("district: 11 features")).toBeTruthy();
    expect(screen.getByText(/detailed state risk not available/)).toBeTruthy();
  });
  it("shows 25 pilot zones, C03 risk details, and reversible breadcrumbs", async () => {
    mount(`?state=IN-MZ&district=${AIZAWL}`);
    expect(await screen.findByText("zone: 25 features")).toBeTruthy();
    expect(screen.getByTestId("map").getAttribute("data-focus-count")).toBe("25");
    await userEvent.click(screen.getByRole("button", { name: "C03" }));
    expect(await screen.findByText("0.7103")).toBeTruthy();
    expect(within(document.querySelector(".gis-context-hud")!).getByRole("heading", { name: "Aizawl" })).toBeTruthy();
    expect(within(document.querySelector(".gis-context-hud")!).queryByRole("heading", { name: "C03" })).toBeNull();
    expect(screen.getByText("0.9276")).toBeTruthy();
    expect(screen.queryByText("0.6200")).toBeNull();
    expect(screen.getByText("REAL_SOIL_MOISTURE")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Aizawl", exact: true }));
    await waitFor(() => expect(screen.queryByLabelText("Zone C03 details")).toBeNull());
    await userEvent.click(screen.getByRole("button", { name: "Mizoram", exact: true }));
    expect(await screen.findByText("district: 11 features")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "North-East India", exact: true }));
    expect(await screen.findByText("state: 8 features")).toBeTruthy();
  });
  it("shows boundary-only status for exact Anjaw and no risk", async () => {
    mount("?state=IN-AR&district=IND-ADM2-76128533B55878637000592");
    expect(await screen.findByText("district: 1 features")).toBeTruthy();
    expect(screen.getByText(/detailed model not implemented/)).toBeTruthy();
    expect(screen.queryByText("Relative Risk")).toBeNull();
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes("/risk/"))).toBe(false);
  });
  it("sanitizes hierarchy API failures and offers retry", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "password=secret SQL trace" }, 503)));
    mount();
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText(/password=secret/)).toBeNull();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });
  it("rejects a URL with an unknown district", async () => {
    mount("?state=IN-MZ&district=UNKNOWN");
    expect(await screen.findByText("This geographic selection was not found.")).toBeTruthy();
  });
  it("does not fabricate risk on API failure", async () => {
    const original = fetch;
    vi.stubGlobal("fetch", vi.fn((url: any, opts: any) => String(url).includes("/risk/") ? response({}, 503) : original(url, opts)));
    mount(`?state=IN-MZ&district=${AIZAWL}&zone=C03`);
    expect(await screen.findByText("Risk data unavailable. Boundaries remain visible.")).toBeTruthy();
    expect(screen.queryByText("0.7103")).toBeNull();
  });
  it("shows explanation unavailable without contributors", () => {
    render(<ZoneInspector zone="C03" loading={false} />);
    expect(screen.getByText("Explanation unavailable")).toBeTruthy();
  });
  it("binds the real canonical 25 geometries without changing them", () => {
    const mapped = pilotZones(grid, info, AIZAWL);
    expect(mapped.features).toHaveLength(25);
    expect(mapped.features.map(f => f.geometry)).toEqual(grid.features.map((f: any) => f.geometry));
    expect(new Set(mapped.features.map(f => f.properties.district_id))).toEqual(new Set([AIZAWL]));
  });
  it("clears descendant selections and labels unknown risk honestly", () => {
    expect(selectLevel({ state: "IN-MZ", district: AIZAWL, zone: "C03" }, "state", "IN-AS")).toEqual({ state: "IN-AS" });
    expect(riskLabel("VERY_HIGH")).toBe("VERY HIGH");
    expect(riskLabel("UNKNOWN")).toBe("Risk unavailable");
  });
  it("caches canonical requests without caching failures", async () => {
    await spatialFetch("/regions/NER/states?include_geometry=true");
    await spatialFetch("/regions/NER/states?include_geometry=true");
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("keeps 2D as default and offers all basemaps while 3D is limited to Aizawl", async () => {
    mount();
    await screen.findByText("state: 8 features");
    expect(screen.queryByTestId("terrain-map")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    const menu = screen.getByRole("dialog", { name: "Map view settings" });
    expect(within(menu).getByRole("button", { name: /Street/ })).toBeTruthy();
    expect(within(menu).getByRole("button", { name: /Terrain/ })).toBeTruthy();
    expect(within(menu).getByRole("button", { name: /Satellite/ })).toBeTruthy();
    const threeD = within(menu).getByRole("button", { name: /3D.*Aizawl detailed pilot/ }) as HTMLButtonElement;
    expect(threeD.disabled).toBe(true);
  });
  it("keeps basemap and mode independent and preserves C03 through 2D and 3D", async () => {
    mount(`?state=IN-MZ&district=${AIZAWL}&zone=C03`);
    expect(await screen.findByText("0.7103")).toBeTruthy();
    expect(screen.getByTestId("map")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /Satellite/ }));
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /^3D/ }));
    const terrain = await screen.findByTestId("terrain-map");
    expect(terrain.getAttribute("data-basemap")).toBe("satellite");
    expect(terrain.getAttribute("data-selected")).toBe("C03");
    expect(screen.getByText("0.9276")).toBeTruthy();
    expect(screen.getByText("REAL_SOIL_MOISTURE")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Map View/ }).textContent).toContain("Satellite · 3D");
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /^2D/ }));
    expect(await screen.findByTestId("map")).toBeTruthy();
    expect(screen.getByText("0.7103")).toBeTruthy();
  });
  it("returns explicitly to 2D when the terrain renderer fails", async () => {
    mount(`?state=IN-MZ&district=${AIZAWL}&zone=C03`);
    await screen.findByText("0.7103");
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /^3D/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Fail terrain" }));
    expect(await screen.findByTestId("map")).toBeTruthy();
    expect(screen.getByText(/returned to 2D/)).toBeTruthy();
    expect(screen.getByText("0.7103")).toBeTruthy();
  });
  it("does not offer 3D when WebGL2 is unavailable", async () => {
    vi.mocked(HTMLCanvasElement.prototype.getContext).mockReturnValue(null);
    mount(`?state=IN-MZ&district=${AIZAWL}`);
    await screen.findByText("zone: 25 features");
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    const threeD = within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /3D.*unavailable on this device/ }) as HTMLButtonElement;
    expect(threeD.disabled).toBe(true);
  });
  it("keeps an in-flight Aizawl risk request alive while selecting a zone", async () => {
    const baseFetch = fetch;
    let resolveRisk!: (value: Response) => void;
    const delayedRisk = new Promise<Response>(resolve => { resolveRisk = resolve; });
    vi.stubGlobal("fetch", vi.fn((url: any, options?: any) => String(url).includes("/risk/current") ? delayedRisk : baseFetch(url, options)));
    mount(`?state=IN-MZ&district=${AIZAWL}`);
    await screen.findByText("zone: 25 features");
    await userEvent.click(screen.getByRole("button", { name: "C03" }));
    resolveRisk(await response({ zones: [risk] }));
    expect(await screen.findByText("0.7103")).toBeTruthy();
    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/risk/current"))).toHaveLength(1);
  });
  it("invalidates an in-flight Aizawl risk response after leaving the pilot", async () => {
    const baseFetch = fetch;
    let resolveRisk!: (value: Response) => void;
    const delayedRisk = new Promise<Response>(resolve => { resolveRisk = resolve; });
    vi.stubGlobal("fetch", vi.fn((url: any, options?: any) => String(url).includes("/risk/current") ? delayedRisk : baseFetch(url, options)));
    mount(`?state=IN-MZ&district=${AIZAWL}`);
    await screen.findByText("zone: 25 features");
    await userEvent.click(screen.getByRole("button", { name: /District.*Aizawl/ }));
    await userEvent.click(screen.getByRole("option", { name: /Champhai/ }));
    expect(await screen.findByText("district: 1 features")).toBeTruthy();
    resolveRisk(await response({ zones: [risk] }));
    await waitFor(() => expect(screen.queryByText("0.7103")).toBeNull());
    expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).includes("/risk/current"))).toHaveLength(1);
  });
  it("lazy-loads each operational dataset once and reuses it across 2D and 3D", async () => {
    mount(`?state=IN-MZ&district=${AIZAWL}`);
    await screen.findByText("zone: 25 features");
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes("/geodata/osm/"))).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: /Layers/ }));
    const menu = screen.getByRole("dialog", { name: "Operational layers" });
    await userEvent.click(within(menu).getByRole("checkbox", { name: /Essential facilities/ }));
    await userEvent.click(within(menu).getByRole("checkbox", { name: /Road network/ }));
    expect(await screen.findByText("Hospital")).toBeTruthy();
    expect(screen.getByText("Clinic")).toBeTruthy();
    expect(screen.getByText("Police")).toBeTruthy();
    expect(screen.queryByText(/Fire Station/i)).toBeNull();
    expect(screen.queryByText(/Community Centre|Shelter/i)).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /^3D/ }));
    await screen.findByTestId("terrain-map");
    await userEvent.click(screen.getByRole("button", { name: /Map View/ }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Map view settings" })).getByRole("button", { name: /^2D/ }));
    await screen.findByTestId("map");

    const urls = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(urls.filter(url => url.endsWith("/geodata/osm/critical-facilities"))).toHaveLength(1);
    expect(urls.filter(url => url.endsWith("/geodata/osm/roads"))).toHaveLength(1);
    expect(urls.some(url => url.includes("raw=true"))).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: /Layers/ }));
    const reopened = screen.getByRole("dialog", { name: "Operational layers" });
    await userEvent.click(within(reopened).getByRole("checkbox", { name: /Essential facilities/ }));
    await userEvent.click(within(reopened).getByRole("checkbox", { name: /Essential facilities/ }));
    expect(vi.mocked(fetch).mock.calls.map(([url]) => String(url)).filter(url => url.endsWith("/geodata/osm/critical-facilities"))).toHaveLength(1);
  });
  it("closes the Layers menu with Escape or an outside click and reports non-pilot unavailability", async () => {
    mount();
    await screen.findByText("state: 8 features");
    await userEvent.click(screen.getByRole("button", { name: /Layers/ }));
    expect(screen.getByText("Available only for the Aizawl detailed pilot.")).toBeTruthy();
    expect((screen.getByRole("checkbox", { name: /Essential facilities/ }) as HTMLInputElement).disabled).toBe(true);
    expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes("/geodata/osm/"))).toBe(false);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Operational layers" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /Layers/ }));
    await userEvent.click(document.body);
    expect(screen.queryByRole("dialog", { name: "Operational layers" })).toBeNull();
  });
});
