// ============================================================
// useGeoJSONData — loads all four sample GeoJSON layers
// Phase 2: fetches from /data/sample/ (frontend public directory)
// Phase 5+: data source swapped per layer (OSM real / API)
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
}

const BASE = "/data/sample";

async function fetchLayer(path: string): Promise<FeatureCollection> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${path}`);
  return res.json() as Promise<FeatureCollection>;
}

export function useGeoJSONData(): GeoJSONData {
  const [state, setState] = useState<GeoJSONData>({
    gridRisk: null,
    roads: null,
    villages: null,
    hospitals: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchLayer(`${BASE}/grid-risk.geojson`),
      fetchLayer(`${BASE}/roads.geojson`),
      fetchLayer(`${BASE}/villages.geojson`),
      fetchLayer(`${BASE}/hospitals.geojson`),
    ])
      .then(([gridRisk, roads, villages, hospitals]) => {
        if (!cancelled) {
          setState({ gridRisk, roads, villages, hospitals, loading: false, error: null });
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: String(err),
          }));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
