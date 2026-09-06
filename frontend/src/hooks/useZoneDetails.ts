// ============================================================
// useZoneDetails — fetches zone forecast from FastAPI backend.
// Falls back to local GeoJSON-derived data if the backend is down.
//
// source = "api"   → data from /risk/forecast/{zone_id}
// source = "local" → data derived from GeoJSON via zoneTransformers
// source = null    → no zone selected
// ============================================================

import { useState, useEffect } from "react";
import type { ZoneForecast } from "../types";
import type { ZoneGeoJSONProperties } from "../types/geojson";
import { getZoneForecast } from "../services/api";
import { propsToForecast } from "../utils/zoneTransformers";

export type ForecastSource = "api" | "local" | null;

export interface ZoneDetailsResult {
  forecast: ZoneForecast | null;
  loading: boolean;
  apiOnline: boolean | null; // null = not yet attempted
  source: ForecastSource;
  error: string | null;
}

export function useZoneDetails(
  zoneId: string | null,
  localProps: ZoneGeoJSONProperties | null
): ZoneDetailsResult {
  const [apiForecast, setApiForecast] = useState<ZoneForecast | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!zoneId) {
      setApiForecast(null);
      setError(null);
      setApiOnline(null);
      return;
    }

    setLoading(true);
    setError(null);

    getZoneForecast(zoneId)
      .then((data) => {
        setApiForecast(data);
        setApiOnline(true);
        setLoading(false);
      })
      .catch((err: unknown) => {
        // Backend down or CORS error → fall back gracefully to local data.
        setApiForecast(null);
        setApiOnline(false);
        setError(String(err));
        setLoading(false);
      });
  }, [zoneId]);

  // Prefer API data when available
  if (apiForecast) {
    return { forecast: apiForecast, loading, apiOnline: true, source: "api", error: null };
  }

  // Fall back to local transformer data
  const localForecast = localProps ? propsToForecast(localProps) : null;
  return {
    forecast: localForecast,
    loading,
    apiOnline,
    source: localProps ? "local" : null,
    error,
  };
}
