import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Feature, GeoJsonProperties, Geometry } from "geojson";
import type { HierarchyMapProps } from "./HierarchyMap";
import { BASEMAPS, TERRAIN_ATTRIBUTION, TERRAIN_TILEJSON_URL } from "./mapConfig";
import type { BasemapId } from "./mapConfig";
import { riskColors, riskLabel } from "../../utils/navigation";
import "maplibre-gl/dist/maplibre-gl.css";

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
  const activeBasemap = useRef(basemap);
  const failed = useRef(false);
  const onSelectRef = useRef(onSelect);
  const [basemapUnavailable, setBasemapUnavailable] = useState(false);
  const [styleReady, setStyleReady] = useState(false);
  const reducedMotion = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  const mappedData = useMemo(() => withRiskProperties(data, risks), [data, risks]);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!container.current) return;
    const fail = (message: string) => {
      if (failed.current) return;
      failed.current = true;
      onFailure(message);
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
            aizawlDem: { type: "raster-dem", url: TERRAIN_TILEJSON_URL, tileSize: 256, encoding: "terrarium", attribution: TERRAIN_ATTRIBUTION },
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
      const property = `${level}_id`;
      const id = event.features?.[0]?.properties?.[property];
      if (typeof id === "string") onSelectRef.current(id);
    };
    const pointer = () => { map.getCanvas().style.cursor = "pointer"; };
    const unpointer = () => { map.getCanvas().style.cursor = ""; };

    map.once("load", () => {
      if (failed.current) return;
      if (context) {
        map.addSource("hierarchy-context", { type: "geojson", data: context });
        map.addLayer({ id: "hierarchy-context-line", type: "line", source: "hierarchy-context", paint: { "line-color": "#82919b", "line-width": 2, "line-dasharray": [2, 2] } });
      }
      map.addSource("hierarchy-data", { type: "geojson", data: mappedData });
      map.addLayer({ id: "hierarchy-fill", type: "fill", source: "hierarchy-data", paint: {
        "fill-color": level === "zone" ? ["coalesce", ["get", "terrain_risk_color"], "#8b98a6"] : "#4da7b6",
        "fill-opacity": level === "zone" ? 0.67 : 0.16,
      } });
      map.addLayer({ id: "hierarchy-line", type: "line", source: "hierarchy-data", paint: { "line-color": "#26343d", "line-width": 1.4 } });
      map.addLayer({ id: "hierarchy-selected", type: "line", source: "hierarchy-data", filter: ["==", ["get", `${level}_id`], selected ?? ""], paint: { "line-color": "#ffffff", "line-width": 3.4 } });
      map.on("click", "hierarchy-fill", selectFeature);
      map.on("mouseenter", "hierarchy-fill", pointer);
      map.on("mouseleave", "hierarchy-fill", unpointer);
      const bounds = boundsOf(focus.features as Feature[]);
      if (bounds) map.fitBounds(bounds, { padding: 52, maxZoom: 14, pitch: 54, bearing: -24, duration: reducedMotion ? 0 : 650 });
      setStyleReady(true);
    });

    return () => {
      canvas.removeEventListener("webglcontextlost", contextLost);
      map.off("error", onError);
      if (map.getLayer("hierarchy-fill")) {
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
    const map = mapRef.current;
    if (!map || !styleReady || activeBasemap.current === basemap) return;
    replaceBasemap(map, basemap);
    activeBasemap.current = basemap;
    setBasemapUnavailable(false);
  }, [basemap, styleReady]);

  useEffect(() => {
    const map = mapRef.current;
    const source = map?.getSource("hierarchy-data") as maplibregl.GeoJSONSource | undefined;
    if (!source) return;
    source.setData(mappedData as GeoJSON.FeatureCollection<Geometry, GeoJsonProperties>);
    if (map?.getLayer("hierarchy-selected")) {
      map.setFilter("hierarchy-selected", ["==", ["get", `${level}_id`], selected ?? ""]);
    }
  }, [level, mappedData, selected]);

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
