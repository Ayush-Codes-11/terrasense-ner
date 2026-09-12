import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { readFileSync } from "node:fs";
import Dashboard from "../src/pages/Dashboard";
import ZoneInspector from "../src/components/dashboard/ZoneInspector";
import { AIZAWL, pilotZones, riskLabel, selectLevel } from "../src/utils/navigation";
import { clearSpatialCache, spatialFetch } from "../src/services/spatial";

vi.mock("../src/components/map/HierarchyMap", () => ({ default: ({ data, level }: any) => <div data-testid="map">{level}: {data.features.length} features</div> }));
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
function response(body: unknown, status = 200) { return Promise.resolve({ ok: status === 200, status, json: async () => body } as Response); }
function mount(search = "") { return render(<MemoryRouter initialEntries={["/" + search]}><Dashboard /></MemoryRouter>); }
beforeEach(() => {
  clearSpatialCache();
  vi.stubGlobal("fetch", vi.fn((url: string) => {
    if (url.includes("/regions/NER/states")) return response(states);
    if (url.includes("/states/")) return response({ ...districts, features: districts.features.filter((f: any) => url.includes(f.properties.state_id)) });
    if (url.includes("/districts/")) return response(url.includes(AIZAWL) ? info : { count: 0, items: [], detailed_zone_model_available: false });
    if (url.endsWith("/zones")) return response(grid);
    if (url.includes("/risk/current")) return response({ zones: [risk] });
    if (url.includes("/weather/")) return response({ forecast_interval_mm: { "0_24h": 10.9 }, observation_timestamp: "2026-09-08T23:59:59Z" });
    return response({}, 404);
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("GIS command centre", () => {
  it("starts at eight states and navigates to 11 Mizoram districts", async () => {
    mount();
    expect(await screen.findByText("state: 8 features")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /Mizoram/ }));
    expect(await screen.findByText("district: 11 features")).toBeTruthy();
    expect(screen.getByText(/Detailed risk model not yet available at state/)).toBeTruthy();
  });
  it("shows 25 pilot zones, C03 risk details, and reversible breadcrumbs", async () => {
    mount(`?state=IN-MZ&district=${AIZAWL}`);
    expect(await screen.findByText("zone: 25 features")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /C03/ }));
    expect(await screen.findByText("0.7103")).toBeTruthy();
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
    expect(screen.getAllByText("Detailed model not implemented").length).toBeGreaterThan(0);
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
});
