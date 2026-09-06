// ============================================================
// useGeoJSONData — loads hazard grid and infrastructure layers
// Phase 6: loads real OSM layers from backend /geodata/osm/*
// with automatic fallback to public /data/sample/*.geojson
// ============================================================

import { useState, useEffect } from "react";
import type { FeatureCollection } from "geojson";

export interface GeoJSONData {
  gridRisk: FeatureCollection | null;
  roads: FeatureCollection | null;
  villages: FeatureCollection | null;
  hospitals: FeatureCollection | null;
  loading: boolean;
  error: string | null;
  osmStatus: "OSM snapshot" | "Cached OSM" | "Sample fallback";
  isRealOsm: boolean;
}

const SAMPLE_BASE = "/data/sample";
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${url}`);
  return res.json() as Promise<T>;
}

export function useGeoJSONData(): GeoJSONData {
  const [state, setState] = useState<GeoJSONData>({
    gridRisk: null,
    roads: null,
    villages: null,
    hospitals: null,
    loading: true,
    error: null,
    osmStatus: "Sample fallback",
    isRealOsm: false,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadAll() {
      // 1. Always load hazard grid from local sample geometry
      let gridRisk: FeatureCollection | null = null;
      try {
        gridRisk = await fetchJSON<FeatureCollection>(`${SAMPLE_BASE}/grid-risk.geojson`);
      } catch (e) {
        console.warn("Could not load grid-risk.geojson", e);
      }

      // 2. Try loading real OSM layers from backend
      try {
        const [statusRes, roadsFc, settlementsFc, facilitiesFc] = await Promise.all([
          fetchJSON<{ status: string; is_real: boolean }>(`${API_BASE}/geodata/osm/status`),
          fetchJSON<FeatureCollection>(`${API_BASE}/geodata/osm/roads`),
          fetchJSON<FeatureCollection>(`${API_BASE}/geodata/osm/settlements`),
          fetchJSON<FeatureCollection>(`${API_BASE}/geodata/osm/critical-facilities`),
        ]);

        if (!cancelled) {
          const statusVal =
            statusRes.status === "OSM snapshot"
              ? "OSM snapshot"
              : statusRes.status === "Cached OSM"
                ? "Cached OSM"
                : "Sample fallback";

          setState({
            gridRisk,
            roads: roadsFc,
            villages: settlementsFc,
            hospitals: facilitiesFc,
            loading: false,
            error: null,
            osmStatus: statusVal,
            isRealOsm: statusRes.is_real,
          });
          return;
        }
      } catch {
        // Backend offline or real OSM unavailable -> fallback to local sample layers
      }

      // 3. Fallback to sample layers
      try {
        const [sampleRoads, sampleVillages, sampleHospitals] = await Promise.all([
          fetchJSON<FeatureCollection>(`${SAMPLE_BASE}/roads.geojson`),
          fetchJSON<FeatureCollection>(`${SAMPLE_BASE}/villages.geojson`),
          fetchJSON<FeatureCollection>(`${SAMPLE_BASE}/hospitals.geojson`),
        ]);

        if (!cancelled) {
          setState({
            gridRisk,
            roads: sampleRoads,
            villages: sampleVillages,
            hospitals: sampleHospitals,
            loading: false,
            error: null,
            osmStatus: "Sample fallback",
            isRealOsm: false,
          });
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: String(err),
          }));
        }
      }
    }

    loadAll();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
