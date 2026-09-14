import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, waitFor } from "@testing-library/react";
import type { Boundaries } from "../src/services/spatial";

const maplibre = vi.hoisted(() => {
  type Handler = (event?: unknown) => void;
  const handlers = new Map<string, Set<Handler>>();
  const sources = new Map<string, unknown>();
  const layers = new Set<string>();
  const source = { setData: vi.fn() };
  const canvas = document.createElement("canvas");
  let styleLoaded = true;
  let terrain: unknown;
  const handlerKey = (name: string, layer?: string) => layer ? `${name}:${layer}` : name;
  const addHandler = (key: string, handler: Handler) => {
    const registered = handlers.get(key) ?? new Set<Handler>();
    registered.add(handler);
    handlers.set(key, registered);
  };
  const map = {
    addControl: vi.fn(),
    getCanvas: vi.fn(() => canvas),
    on: vi.fn((name: string, layerOrHandler: string | Handler, handler?: Handler) => {
      addHandler(handlerKey(name, typeof layerOrHandler === "string" ? layerOrHandler : undefined), handler ?? layerOrHandler as Handler);
      return map;
    }),
    off: vi.fn((name: string, layerOrHandler: string | Handler, handler?: Handler) => {
      const key = handlerKey(name, typeof layerOrHandler === "string" ? layerOrHandler : undefined);
      handlers.get(key)?.delete(handler ?? layerOrHandler as Handler);
      return map;
    }),
    addSource: vi.fn((id: string, specification: unknown) => {
      sources.set(id, id.startsWith("hierarchy-") ? source : specification);
    }),
    addLayer: vi.fn((layer: { id: string }) => { layers.add(layer.id); }),
    removeLayer: vi.fn((id: string) => { layers.delete(id); }),
    removeSource: vi.fn((id: string) => { sources.delete(id); }),
    fitBounds: vi.fn(),
    getSource: vi.fn((id: string) => sources.get(id)),
    getLayer: vi.fn((id: string) => layers.has(id) ? { id } : undefined),
    setFilter: vi.fn(),
    setPaintProperty: vi.fn(),
    isStyleLoaded: vi.fn(() => styleLoaded),
    getTerrain: vi.fn(() => terrain),
    setTerrain: vi.fn((value: unknown) => { terrain = value; }),
    remove: vi.fn(),
  };
  const MapConstructor = vi.fn(function MapMock(options: { style: { sources: Record<string, unknown>; layers: Array<{ id: string }>; terrain?: unknown } }) {
    sources.clear();
    layers.clear();
    Object.entries(options.style.sources).forEach(([id, specification]) => sources.set(id, specification));
    options.style.layers.forEach(layer => layers.add(layer.id));
    terrain = options.style.terrain;
    return map;
  });
  const emit = (name: string, event?: unknown) => handlers.get(name)?.forEach(handler => handler(event));
  const resetStyle = () => { sources.clear(); layers.clear(); terrain = undefined; };
  const setStyleLoaded = (value: boolean) => { styleLoaded = value; };
  return { handlers, sources, layers, source, canvas, map, Map: MapConstructor, emit, resetStyle, setStyleLoaded, setWorkerUrl: vi.fn() };
});

vi.mock("maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url", () => ({ default: "/assets/maplibre-worker.js" }));
vi.mock("maplibre-gl", () => ({
  Map: maplibre.Map,
  NavigationControl: vi.fn(function NavigationControlMock() {}),
  ScaleControl: vi.fn(function ScaleControlMock() {}),
  setWorkerUrl: maplibre.setWorkerUrl,
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
  maplibre.sources.clear();
  maplibre.layers.clear();
  maplibre.setStyleLoaded(true);
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
    maplibre.emit("error", { sourceId: "aizawlDem", error: { message: "secret provider detail" } });
    expect(onFailure).toHaveBeenCalledWith("Aizawl terrain tiles are unavailable. The map has returned to 2D.");
    expect(onFailure.mock.calls.flat().join(" ")).not.toContain("secret provider detail");
  });

  it("returns to 2D if the WebGL context is lost", () => {
    const onFailure = vi.fn();
    render(<TerrainMap3D data={zones} focus={zones} level="zone" risks={[]} basemap="street" onSelect={vi.fn()} onFailure={onFailure} />);
    maplibre.canvas.dispatchEvent(new Event("webglcontextlost", { cancelable: true }));
    expect(onFailure).toHaveBeenCalledWith("The 3D graphics context was lost. The map has returned to 2D.");
  });

  it("waits for style readiness and reinstalls hierarchy idempotently after a style reload", () => {
    maplibre.setStyleLoaded(false);
    const props = { data: zones, focus: zones, context: zones, level: "zone" as const, selected: "C03", risks: [{ zone_id: "C03", risk_score: .7103, risk_category: "HIGH" }], basemap: "terrain" as const, onSelect: vi.fn(), onFailure: vi.fn() };
    const view = render(<TerrainMap3D {...props} />);

    expect(maplibre.map.addSource).not.toHaveBeenCalledWith("hierarchy-data", expect.anything());
    maplibre.setStyleLoaded(true);
    act(() => maplibre.emit("style.load"));

    expect(maplibre.sources.has("hierarchy-data")).toBe(true);
    expect(maplibre.sources.has("hierarchy-context")).toBe(true);
    expect(maplibre.layers.has("hierarchy-fill")).toBe(true);
    expect(maplibre.layers.has("hierarchy-line")).toBe(true);
    expect(maplibre.layers.has("hierarchy-selected")).toBe(true);
    expect(maplibre.map.on.mock.calls.filter(call => call[0] === "click" && call[1] === "hierarchy-fill")).toHaveLength(1);

    maplibre.resetStyle();
    act(() => {
      maplibre.emit("style.load");
      maplibre.emit("style.load");
    });

    for (const id of ["hierarchy-context-line", "hierarchy-fill", "hierarchy-line", "hierarchy-selected"]) {
      expect(maplibre.map.addLayer.mock.calls.filter(call => call[0].id === id)).toHaveLength(2);
    }
    expect(maplibre.map.on.mock.calls.filter(call => call[0] === "click" && call[1] === "hierarchy-fill")).toHaveLength(1);

    view.rerender(<TerrainMap3D {...props} risks={[{ zone_id: "C03", risk_score: .7103, risk_category: "VERY_HIGH" }]} />);
    expect(maplibre.source.setData).toHaveBeenCalled();

    view.unmount();
    expect(maplibre.map.off).toHaveBeenCalledWith("load", expect.any(Function));
    expect(maplibre.map.off).toHaveBeenCalledWith("style.load", expect.any(Function));
    expect(maplibre.map.off).toHaveBeenCalledWith("click", "hierarchy-fill", expect.any(Function));
  });

  it("replaces the 3D basemap after load even while source tiles are pending", async () => {
    const props = { data: zones, focus: zones, level: "zone" as const, risks: [], onSelect: vi.fn(), onFailure: vi.fn() };
    const view = render(<TerrainMap3D {...props} basemap="terrain" />);
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
