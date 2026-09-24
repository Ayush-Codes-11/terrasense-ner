import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ZoneInspector from "../src/components/dashboard/ZoneInspector";
import type { RiskRecord, ZoneExposure } from "../src/services/spatial";

const summary = {
  osm_road_segments_count: 277,
  motorable_road_segments_count: 241,
  motorable_road_km: 49.85,
  total_road_km: 52.092,
  pedestrian_road_km: 2.242,
  track_road_km: 0,
  mapped_communities: 1,
  critical_facilities: 5,
  roads_blocked: 0,
  roads_exposed: 277,
  roads_exposed_km: 49.85,
  villages_exposed: 1,
  hospitals_exposed: 5,
};
const exposure = (zoneId: string, facilities = 5): ZoneExposure => ({
  zone_id: zoneId,
  summary: { ...summary, critical_facilities: facilities },
  roads: [], settlements: [], critical_facilities: [],
  hazard_geometry: "SAMPLE_MOCK",
  exposure_features: "REAL_OSM",
  analysis_mode: "PROTOTYPE_MIXED_PROVENANCE",
  data_meta: { data_type: "REAL_OSM", source: "OpenStreetMap contributors via Overpass API", timestamp: "2026-09-23T10:00:00Z", is_live: false },
});
const risk: RiskRecord = { zone_id: "C03", risk_score: .7103, risk_category: "HIGH", normalized_features: { soil_wetness: .9276 }, feature_provenance: { soil_wetness: "REAL_SOIL_MOISTURE" } };
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status === 200, status, json: async () => body } as Response);
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Exposure & Access", () => {
  it("renders the typed successful response with truthful provenance and methodology", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(exposure("C03"))));
    render(<ZoneInspector zone="C03" risk={risk} loading={false} />);
    expect(await screen.findByText("49.85 km")).toBeTruthy();
    expect(screen.getByText("52.09 km")).toBeTruthy();
    expect(screen.getByText("2.24 km")).toBeTruthy();
    expect(screen.getByText(/cached OSM snapshot/)).toBeTruthy();
    expect(screen.getByText(/geodesic lengths of mapped OSM features clipped to the selected zone/)).toBeTruthy();
    expect(screen.getByText(/does not establish current road passability or verified blockage/)).toBeTruthy();
    expect(screen.getByText("NASA SMAP L4 (real satellite soil moisture)")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/unaffected road|safely accessible/i);
  });

  it("shows loading and unavailable states with retry", async () => {
    const pending = deferred<Response>();
    const fetchMock = vi.fn(() => pending.promise);
    vi.stubGlobal("fetch", fetchMock);
    render(<ZoneInspector zone="C03" loading={false} />);
    expect(screen.getByText("Calculating mapped exposure…")).toBeTruthy();
    pending.resolve(await response({}, 503));
    expect(await screen.findByText("Exposure calculations are temporarily unavailable.")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Retry exposure" }));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("clears old-zone data immediately and rejects a stale response", async () => {
    const c03 = deferred<Response>();
    const c04 = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn((url: string) => url.endsWith("C03") ? c03.promise : c04.promise));
    const view = render(<ZoneInspector zone="C03" loading={false} />);
    view.rerender(<ZoneInspector zone="C04" loading={false} />);
    expect(screen.queryByText("49.85 km")).toBeNull();
    c04.resolve(await response(exposure("C04", 2)));
    expect(await screen.findByText("2")).toBeTruthy();
    c03.resolve(await response(exposure("C03", 9)));
    await waitFor(() => expect(screen.queryByText("9")).toBeNull());
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("aborts the active request on unmount", () => {
    let signal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_url: string, options?: RequestInit) => {
      signal = options?.signal as AbortSignal;
      return new Promise<Response>(() => undefined);
    }));
    const view = render(<ZoneInspector zone="C03" loading={false} />);
    expect(signal?.aborted).toBe(false);
    view.unmount();
    expect(signal?.aborted).toBe(true);
  });
});
