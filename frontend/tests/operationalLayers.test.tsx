import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useOperationalLayers } from "../src/hooks/useOperationalLayers";
import { fetchOperationalFacilities } from "../src/services/spatial";

function Harness() {
  const layers = useOperationalLayers(true);
  return <div>
    <button onClick={layers.toggleFacilities}>Facilities</button>
    <button onClick={layers.toggleRoads}>Roads</button>
    <span>{layers.facilities.state}</span><span>{layers.roads.state}</span>
  </div>;
}
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status === 200, status, json: async () => body } as Response);

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("operational layer data owner", () => {
  it("aborts active dataset and status requests on unmount", async () => {
    const signals: AbortSignal[] = [];
    vi.stubGlobal("fetch", vi.fn((_url: string, options?: RequestInit) => {
      signals.push(options?.signal as AbortSignal);
      return new Promise<Response>(() => undefined);
    }));
    const view = render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Facilities" }));
    await waitFor(() => expect(signals).toHaveLength(2));
    expect(signals.every(signal => !signal.aborted)).toBe(true);
    view.unmount();
    expect(signals.every(signal => signal.aborted)).toBe(true);
  });

  it("labels static fallback data as fictitious sample data", async () => {
    const sample = { type: "FeatureCollection", features: [{ type: "Feature", properties: { facility_type: "hospital" }, geometry: { type: "Point", coordinates: [92.71, 23.73] } }] };
    vi.stubGlobal("fetch", vi.fn((url: string) => url.includes("/geodata/osm/critical-facilities") ? response({}, 503) : response(sample)));
    const result = await fetchOperationalFacilities(new AbortController().signal);
    expect(result.data_meta).toMatchObject({ data_type: "SAMPLE_MOCK", source: "TerraSense sample fallback", is_live: false });
    expect(result.data_meta.note).toContain("Fictitious sample facilities");
  });
});
