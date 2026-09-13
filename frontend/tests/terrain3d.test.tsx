import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, waitFor } from "@testing-library/react";
import type { Boundaries } from "../src/services/spatial";

const maplibre = vi.hoisted(() => {
  const handlers = new Map<string, (event: any) => void>();
  const source = { setData: vi.fn() };
  const canvas = document.createElement("canvas");
  const map = {
    addControl: vi.fn(), getCanvas: vi.fn(() => canvas), on: vi.fn((name: string, layerOrHandler: any, handler?: any) => {
      handlers.set(name, handler ?? layerOrHandler); return map;
    }), off: vi.fn(), once: vi.fn((name: string, handler: () => void) => { if (name === "load") handler(); return map; }),
    addSource: vi.fn(), addLayer: vi.fn(), removeLayer: vi.fn(), removeSource: vi.fn(), setLayoutProperty: vi.fn(), fitBounds: vi.fn(), getSource: vi.fn((id: string) => id === "hierarchy-data" ? source : undefined),
    getLayer: vi.fn((id: string) => id === "hierarchy-fill" || id === "hierarchy-selected"), setFilter: vi.fn(), isStyleLoaded: vi.fn(() => true), remove: vi.fn(),
  };
  return { handlers, source, canvas, map, Map: vi.fn(function MapMock() { return map; }) };
});

vi.mock("maplibre-gl", () => ({
  Map: maplibre.Map,
  NavigationControl: vi.fn(function NavigationControlMock() {}),
  ScaleControl: vi.fn(function ScaleControlMock() {}),
}));

import TerrainMap3D from "../src/components/map/TerrainMap3D";

const zones: Boundaries = {
  type: "FeatureCollection",
  features: Array.from({ length: 25 }, (_, index) => ({
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [[[92.70, 23.72], [92.71, 23.72], [92.71, 23.73], [92.70, 23.72]]] },
    properties: { zone_id: index === 2 ? "C03" : `Z${index}` },
  })),
};

beforeEach(() => {
  maplibre.handlers.clear();
  Object.values(maplibre.map).forEach(value => { if (typeof value === "function" && "mockClear" in value) (value as any).mockClear(); });
  maplibre.source.setData.mockClear();
  maplibre.Map.mockClear();
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Aizawl terrain renderer", () => {
  it("creates genuine terrain at scale 1, renders 25 zones, and releases MapLibre", () => {
    const view = render(<TerrainMap3D data={zones} focus={zones} level="zone" selected="C03" risks={[{ zone_id: "C03", risk_score: .7103, risk_category: "HIGH" }]} basemap="terrain" onSelect={vi.fn()} onFailure={vi.fn()} />);
    expect(maplibre.Map).toHaveBeenCalledOnce();
    const options = maplibre.Map.mock.calls[0][0] as any;
    expect(options.style.terrain).toEqual({ source: "aizawlDem", exaggeration: 1 });
    expect(options.style.sources.aizawlDem).toMatchObject({ type: "raster-dem", encoding: "terrarium", url: "/terrain/aizawl/v1/tiles.json" });
    expect(maplibre.map.addSource).toHaveBeenCalledWith("hierarchy-data", expect.objectContaining({ type: "geojson" }));
    expect(maplibre.map.fitBounds).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ duration: 0, pitch: 54 }));
    view.unmount();
    expect(maplibre.map.remove).toHaveBeenCalledOnce();
  });

  it("sanitizes terrain-source failure and requests explicit fallback", () => {
    const onFailure = vi.fn();
    render(<TerrainMap3D data={zones} focus={zones} level="zone" risks={[]} basemap="terrain" onSelect={vi.fn()} onFailure={onFailure} />);
    maplibre.handlers.get("error")?.({ sourceId: "aizawlDem", error: { message: "secret provider detail" } });
    expect(onFailure).toHaveBeenCalledWith("Aizawl terrain tiles are unavailable. The map has returned to 2D.");
    expect(onFailure.mock.calls.flat().join(" ")).not.toContain("secret provider detail");
  });

  it("returns to 2D if the WebGL context is lost", () => {
    const onFailure = vi.fn();
    render(<TerrainMap3D data={zones} focus={zones} level="zone" risks={[]} basemap="street" onSelect={vi.fn()} onFailure={onFailure} />);
    maplibre.canvas.dispatchEvent(new Event("webglcontextlost", { cancelable: true }));
    expect(onFailure).toHaveBeenCalledWith("The 3D graphics context was lost. The map has returned to 2D.");
  });

  it("replaces the 3D basemap after load even while source tiles are pending", async () => {
    const props = { data: zones, focus: zones, level: "zone" as const, risks: [], onSelect: vi.fn(), onFailure: vi.fn() };
    const view = render(<TerrainMap3D {...props} basemap="terrain" />);
    maplibre.map.getLayer.mockImplementation((id: string) => id === "basemap-raster" || id === "hierarchy-fill" || id === "hierarchy-selected");
    maplibre.map.getSource.mockImplementation((id: string) => id === "basemap" ? {} : id === "hierarchy-data" ? maplibre.source : undefined);
    maplibre.map.isStyleLoaded.mockReturnValue(false);
    view.rerender(<TerrainMap3D {...props} basemap="satellite" />);
    await waitFor(() => {
      expect(maplibre.map.removeLayer).toHaveBeenCalledWith("basemap-raster");
      expect(maplibre.map.removeSource).toHaveBeenCalledWith("basemap");
      expect(maplibre.map.addSource).toHaveBeenCalledWith("basemap", expect.objectContaining({
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      }));
    });
  });
});
