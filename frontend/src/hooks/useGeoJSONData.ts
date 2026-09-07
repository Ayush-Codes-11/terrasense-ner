// ============================================================
// useGeoJSONData — loads hazard grid and infrastructure layers
// Phase 6: loads real OSM layers from backend /geodata/osm/*
// with automatic fallback to public /data/sample/*.geojson
// Updated: /zones from FastAPI backend is primary source for risk grid,
// with /data/sample/grid-risk.geojson as fallback.
// Validates 25-feature FeatureCollection and exposes explicit error if both fail.
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
const API_BASE = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000"
).replace(/\/+$/, "");

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${url}`);
  return res.json() as Promise<T>;
}

function isValidRiskGrid(data: unknown): data is FeatureCollection {
  if (!data || typeof data !== "object") return false;
  const fc = data as Record<string, unknown>;
  return (
    fc.type === "FeatureCollection" &&
    Array.isArray(fc.features) &&
    fc.features.length === 25
  );
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
      // 1. Load hazard grid: /zones (primary) -> /data/sample/grid-risk.geojson (fallback)
      let gridRisk: FeatureCollection | null = null;
      let gridError: string | null = null;

      try {
        const backendZones = await fetchJSON<unknown>(`${API_BASE}/zones`);
        if (isValidRiskGrid(backendZones)) {
          gridRisk = backendZones;
        } else {
          console.warn("Backend /zones did not return a valid 25-feature FeatureCollection");
        }
      } catch (err) {
        console.warn("Failed to fetch risk grid from backend /zones, attempting fallback", err);
      }

      if (!gridRisk) {
        try {
          const sampleGrid = await fetchJSON<unknown>(`${SAMPLE_BASE}/grid-risk.geojson`);
          if (isValidRiskGrid(sampleGrid)) {
            gridRisk = sampleGrid;
          } else {
            console.warn("Fallback /data/sample/grid-risk.geojson is not a valid 25-feature FeatureCollection");
          }
        } catch (err) {
          console.warn("Failed to fetch fallback /data/sample/grid-risk.geojson", err);
        }
      }

      if (!gridRisk) {
        gridError = "Failed to load risk grid (both backend /zones and fallback /data/sample/grid-risk.geojson failed)";
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
            error: gridError,
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
            error: gridError,
            osmStatus: "Sample fallback",
            isRealOsm: false,
          });
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const combinedError = gridError
            ? `${gridError} | Failed to load sample layers: ${String(err)}`
            : String(err);
          setState((prev) => ({
            ...prev,
            gridRisk,
            loading: false,
            error: combinedError,
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
