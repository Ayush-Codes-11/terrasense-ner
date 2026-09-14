import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { Feature, GeoJsonProperties, Geometry } from "geojson";
import type { HierarchyMapProps } from "./HierarchyMap";
import { BASEMAPS, TERRAIN_ATTRIBUTION, TERRAIN_TILEJSON_URL } from "./mapConfig";
import type { BasemapId } from "./mapConfig";
import { riskColors, riskLabel } from "../../utils/navigation";
import "maplibre-gl/dist/maplibre-gl.css";

maplibregl.setWorkerUrl(maplibreWorkerUrl);

interface Props extends HierarchyMapProps {
  onFailure: (message: string) => void;
}

function boundsOf(features: Feature[]): [[number, number], [number, number]] | undefined {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const visit = (value: unknown) => {
    if (!Array.isArray(value)) return;
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
      west = Math.min(west, value[0]);
      south = Math.min(south, value[1]);
      east = Math.max(east, value[0]);
      north = Math.max(north, value[1]);
      return;
    }
    value.forEach(visit);
  };
  features.forEach(feature => {
    if (feature.geometry && "coordinates" in feature.geometry) visit(feature.geometry.coordinates);
  });
  return Number.isFinite(west) ? [[west, south], [east, north]] : undefined;
}

function withRiskProperties(data: HierarchyMapProps["data"], risks: HierarchyMapProps["risks"]) {
  const byZone = new Map(risks.map(risk => [risk.zone_id, risk]));
  return {
    ...data,
    features: data.features.map(feature => {
      const zoneId = feature.properties.zone_id ?? "";
      const category = byZone.get(zoneId)?.risk_category ?? "";
      return {
        ...feature,
        properties: {
          ...feature.properties,
          terrain_risk_category: category,
          terrain_risk_label: riskLabel(category),
          terrain_risk_color: riskColors[category] ?? "#8b98a6",
        },
      };
    }),
  };
}

function basemapSource(id: BasemapId) {
  const source = BASEMAPS[id];
  return { type: "raster" as const, tiles: [...source.maplibreTiles], tileSize: 256, maxzoom: source.maxZoom, attribution: source.attribution };
}

function terrainSource() {
  return { type: "raster-dem" as const, url: TERRAIN_TILEJSON_URL, tileSize: 256, encoding: "terrarium" as const, attribution: TERRAIN_ATTRIBUTION };
}

function replaceBasemap(map: maplibregl.Map, id: BasemapId) {
  if (map.getLayer("basemap-raster")) map.removeLayer("basemap-raster");
  if (map.getSource("basemap")) map.removeSource("basemap");
  map.addSource("basemap", basemapSource(id));
  const before = map.getLayer("hierarchy-context-line")
    ? "hierarchy-context-line"
    : map.getLayer("hierarchy-fill")
      ? "hierarchy-fill"
      : undefined;
  map.addLayer({ id: "basemap-raster", type: "raster", source: "basemap" }, before);
}

export default function TerrainMap3D({ data, focus, context, level, selected, risks, basemap, onSelect, onFailure }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | undefined>(undefined);
  const installHierarchyRef = useRef<() => void>(() => undefined);
  const fitFocusRef = useRef<() => void>(() => undefined);
  const activeBasemap = useRef(basemap);
  const failed = useRef(false);
  const onSelectRef = useRef(onSelect);
  const onFailureRef = useRef(onFailure);
  const [basemapUnavailable, setBasemapUnavailable] = useState(false);
  const reducedMotion = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  const mappedData = useMemo(() => withRiskProperties(data, risks), [data, risks]);
  const mappedDataRef = useRef(mappedData);
  const focusRef = useRef(focus);
  const contextRef = useRef(context);
  const levelRef = useRef(level);
  const selectedRef = useRef(selected);
  const basemapRef = useRef(basemap);
  onSelectRef.current = onSelect;
  onFailureRef.current = onFailure;
  mappedDataRef.current = mappedData;
  focusRef.current = focus;
  contextRef.current = context;
  levelRef.current = level;
  selectedRef.current = selected;
  basemapRef.current = basemap;

  useEffect(() => {
    if (!container.current) return;
    let disposed = false;
    let hierarchyHandlersInstalled = false;
    let initialFitComplete = false;
    const fail = (message: string) => {
      if (disposed || failed.current) return;
      failed.current = true;
      onFailureRef.current(message);
    };
    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: container.current,
        center: [92.7175, 23.727],
        zoom: 12,
        pitch: 54,
        bearing: -24,
        minZoom: 8,
        maxZoom: 18,
        attributionControl: { compact: true },
        style: {
          version: 8,
          sources: {
            basemap: basemapSource(basemap),
            aizawlDem: terrainSource(),
          },
          layers: [
            { id: "basemap-raster", type: "raster", source: "basemap" },
          ],
          terrain: { source: "aizawlDem", exaggeration: 1 },
        },
      });
    } catch {
      fail("3D terrain is unavailable on this device. The map has returned to 2D.");
      return;
    }
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true, showCompass: true }), "bottom-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

    const canvas = map.getCanvas();
    const contextLost = (event: Event) => {
      event.preventDefault();
      fail("The 3D graphics context was lost. The map has returned to 2D.");
    };
    canvas.addEventListener("webglcontextlost", contextLost);
    const onError = (event: maplibregl.ErrorEvent) => {
      if (disposed) return;
      const sourceId = (event as maplibregl.ErrorEvent & { sourceId?: string }).sourceId;
      const message = event.error?.message ?? "";
      if (sourceId === "aizawlDem" || message.includes("/terrain/aizawl/")) {
        fail("Aizawl terrain tiles are unavailable. The map has returned to 2D.");
      } else if (sourceId === "basemap") {
        setBasemapUnavailable(true);
      }
    };
    map.on("error", onError);
    const selectFeature = (event: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
      const property = `${levelRef.current}_id`;
      const id = event.features?.[0]?.properties?.[property];
      if (typeof id === "string") onSelectRef.current(id);
    };
    const pointer = () => { map.getCanvas().style.cursor = "pointer"; };
    const unpointer = () => { map.getCanvas().style.cursor = ""; };

    const fitFocus = () => {
      if (disposed || !map.isStyleLoaded()) return;
      const bounds = boundsOf(focusRef.current.features as Feature[]);
      if (bounds) map.fitBounds(bounds, { padding: 52, maxZoom: 14, pitch: 54, bearing: -24, duration: reducedMotion ? 0 : 650 });
    };
    fitFocusRef.current = fitFocus;

    const installHierarchy = () => {
      if (disposed || failed.current || !map.isStyleLoaded()) return;

      const currentBasemap = basemapRef.current;
      if (activeBasemap.current !== currentBasemap && map.getSource("basemap")) {
        replaceBasemap(map, currentBasemap);
      } else {
        if (!map.getSource("basemap")) map.addSource("basemap", basemapSource(currentBasemap));
        if (!map.getLayer("basemap-raster")) map.addLayer({ id: "basemap-raster", type: "raster", source: "basemap" });
      }
      activeBasemap.current = currentBasemap;

      if (!map.getSource("aizawlDem")) map.addSource("aizawlDem", terrainSource());
      if (!map.getTerrain()) map.setTerrain({ source: "aizawlDem", exaggeration: 1 });

      const currentContext = contextRef.current;
      const contextSource = map.getSource("hierarchy-context") as maplibregl.GeoJSONSource | undefined;
      if (currentContext) {
        if (contextSource) {
          contextSource.setData(currentContext as GeoJSON.FeatureCollection<Geometry, GeoJsonProperties>);
        } else {
          map.addSource("hierarchy-context", { type: "geojson", data: currentContext });
        }
        if (!map.getLayer("hierarchy-context-line")) {
          map.addLayer({ id: "hierarchy-context-line", type: "line", source: "hierarchy-context", paint: { "line-color": "#82919b", "line-width": 2, "line-dasharray": [2, 2] } });
        }
      } else {
        if (map.getLayer("hierarchy-context-line")) map.removeLayer("hierarchy-context-line");
        if (contextSource) map.removeSource("hierarchy-context");
      }

      const hierarchySource = map.getSource("hierarchy-data") as maplibregl.GeoJSONSource | undefined;
      if (hierarchySource) {
        hierarchySource.setData(mappedDataRef.current as GeoJSON.FeatureCollection<Geometry, GeoJsonProperties>);
      } else {
        map.addSource("hierarchy-data", { type: "geojson", data: mappedDataRef.current });
      }

      const currentLevel = levelRef.current;
      const fillColor = currentLevel === "zone"
        ? ["coalesce", ["get", "terrain_risk_color"], "#8b98a6"] as maplibregl.ExpressionSpecification
        : "#4da7b6";
      const fillOpacity = currentLevel === "zone" ? 0.67 : 0.16;
      if (!map.getLayer("hierarchy-fill")) {
        map.addLayer({ id: "hierarchy-fill", type: "fill", source: "hierarchy-data", paint: { "fill-color": fillColor, "fill-opacity": fillOpacity } });
      } else {
        map.setPaintProperty("hierarchy-fill", "fill-color", fillColor);
        map.setPaintProperty("hierarchy-fill", "fill-opacity", fillOpacity);
      }
      if (!map.getLayer("hierarchy-line")) {
        map.addLayer({ id: "hierarchy-line", type: "line", source: "hierarchy-data", paint: { "line-color": "#26343d", "line-width": 1.4 } });
      }
      if (!map.getLayer("hierarchy-selected")) {
        map.addLayer({ id: "hierarchy-selected", type: "line", source: "hierarchy-data", filter: ["==", ["get", `${currentLevel}_id`], selectedRef.current ?? ""], paint: { "line-color": "#ffffff", "line-width": 3.4 } });
      } else {
        map.setFilter("hierarchy-selected", ["==", ["get", `${currentLevel}_id`], selectedRef.current ?? ""]);
      }

      if (!hierarchyHandlersInstalled) {
        map.on("click", "hierarchy-fill", selectFeature);
        map.on("mouseenter", "hierarchy-fill", pointer);
        map.on("mouseleave", "hierarchy-fill", unpointer);
        hierarchyHandlersInstalled = true;
      }
      if (!initialFitComplete) {
        initialFitComplete = true;
        fitFocus();
      }
    };
    installHierarchyRef.current = installHierarchy;
    const onStyleReady = () => installHierarchy();
    map.on("load", onStyleReady);
    map.on("style.load", onStyleReady);
    installHierarchy();

    return () => {
      disposed = true;
      installHierarchyRef.current = () => undefined;
      fitFocusRef.current = () => undefined;
      canvas.removeEventListener("webglcontextlost", contextLost);
      map.off("error", onError);
      map.off("load", onStyleReady);
      map.off("style.load", onStyleReady);
      if (hierarchyHandlersInstalled) {
        map.off("click", "hierarchy-fill", selectFeature);
        map.off("mouseenter", "hierarchy-fill", pointer);
        map.off("mouseleave", "hierarchy-fill", unpointer);
      }
      map.remove();
      mapRef.current = undefined;
    };
  // The map instance is intentionally created once per 3D renderer mount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    installHierarchyRef.current();
    setBasemapUnavailable(false);
  }, [basemap]);

  useEffect(() => {
    installHierarchyRef.current();
  }, [context, level, mappedData, selected]);

  useEffect(() => {
    fitFocusRef.current();
  }, [focus]);

  return <div className="gis-map gis-map-3d">
    <div ref={container} className="gis-maplibre" aria-label="Interactive Aizawl 3D terrain map" />
    <label className="sr-only">Select analysis zone
      <select value={selected ?? ""} onChange={event => onSelect(event.target.value)}>
        <option value="">Select a zone</option>
        {data.features.map(feature => <option key={feature.properties.zone_id} value={feature.properties.zone_id}>{feature.properties.zone_id}</option>)}
      </select>
    </label>
    <p className="gis-terrain-disclosure">3D terrain · Copernicus GLO-30 DSM · approximately 30 m · not live</p>
    {basemapUnavailable && <p className="gis-tile-notice" role="status">Selected basemap tiles are unavailable. Copernicus terrain and hierarchy overlays remain available.</p>}
  </div>;
}
