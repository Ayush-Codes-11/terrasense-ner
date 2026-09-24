import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import type { Boundaries, OperationalFeatureCollection } from "../src/services/spatial";

const leaflet = vi.hoisted(() => {
  const popupNodes: HTMLElement[] = [];
  class Path {}
  const map = { fitBounds: vi.fn(), invalidateSize: vi.fn(), getContainer: vi.fn(() => document.createElement("div")) };
  const layer = { bindPopup: vi.fn((node: HTMLElement) => { popupNodes.push(node); }), bindTooltip: vi.fn(), on: vi.fn() };
  return { popupNodes, Path, map, layer, circleMarker: vi.fn(() => layer), geoJSON: vi.fn(() => ({ getBounds: () => ({ isValid: () => true }) })) };
});

vi.mock("leaflet", () => ({ default: { Path: leaflet.Path, circleMarker: leaflet.circleMarker, geoJSON: leaflet.geoJSON } }));
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="leaflet-map">{children}</div>,
  TileLayer: () => null,
  ScaleControl: () => null,
  useMap: () => leaflet.map,
  GeoJSON: (props: any) => {
    if (!props.data?.data_meta) return <div data-testid="hierarchy-layer" />;
    const kind = props.data.features[0]?.geometry?.type === "Point" ? "facilities-layer" : "roads-layer";
    if (kind === "facilities-layer") {
      const feature = props.data.features[0];
      props.pointToLayer?.(feature, { lat: 23.73, lng: 92.71 });
      props.onEachFeature?.(feature, leaflet.layer);
    }
    return <div data-testid={kind} />;
  },
}));

import HierarchyMap from "../src/components/map/HierarchyMap";

const zones: Boundaries = { type: "FeatureCollection", features: [{ type: "Feature", properties: { zone_id: "C03" }, geometry: { type: "Polygon", coordinates: [[[92.7, 23.7], [92.71, 23.7], [92.71, 23.71], [92.7, 23.7]]] } }] };
const meta = { data_type: "REAL_OSM", source: "OpenStreetMap contributors", is_live: false };
const roads: OperationalFeatureCollection = { type: "FeatureCollection", data_meta: meta, features: [{ type: "Feature", properties: { highway: "primary" }, geometry: { type: "LineString", coordinates: [[92.7, 23.7], [92.71, 23.71]] } }] };
const facilities: OperationalFeatureCollection = { type: "FeatureCollection", data_meta: meta, features: [{ type: "Feature", properties: { name: "<script>alert(1)</script>", category: "clinic" }, geometry: { type: "Point", coordinates: [92.71, 23.73] } }] };
const baseProps = { data: zones, focus: zones, level: "zone" as const, selected: "C03", risks: [], basemap: "terrain" as const, roads, facilities, onSelect: vi.fn() };

beforeEach(() => {
  leaflet.popupNodes.length = 0;
  leaflet.layer.bindPopup.mockClear();
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("Leaflet operational overlays", () => {
  it("toggles roads and facilities and builds facility popup content with text nodes", () => {
    const view = render(<HierarchyMap {...baseProps} showRoads showFacilities />);
    expect(screen.getByTestId("roads-layer")).toBeTruthy();
    expect(screen.getByTestId("facilities-layer")).toBeTruthy();
    const popup = leaflet.popupNodes[0];
    expect(popup.textContent).toContain("<script>alert(1)</script>");
    expect(popup.querySelector("script")).toBeNull();
    expect(popup.textContent).toContain("Category: Clinic");

    view.rerender(<HierarchyMap {...baseProps} showRoads={false} showFacilities={false} />);
    expect(screen.queryByTestId("roads-layer")).toBeNull();
    expect(screen.queryByTestId("facilities-layer")).toBeNull();
    view.unmount();
  });
});
