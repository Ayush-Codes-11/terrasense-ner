// ============================================================
// useZoneDetails — fetches zone forecast + current risk from FastAPI backend.
// Falls back to local GeoJSON-derived data if the backend is down.
//
// source = "api"             → data from /risk/forecast/{zone_id} & /risk/current/{zone_id}
// source = "sample_fallback" → data derived locally via zoneTransformers
// source = null              → no zone selected
// ============================================================

import { useState, useEffect } from "react";
import type { Zone, ZoneForecast, WhyNowData } from "../types";
import type { ZoneGeoJSONProperties } from "../types/geojson";
import { getZoneForecast, getZoneRisk } from "../services/api";
import {
  propsToForecast,
  propsToZone,
  propsToWhyNow,
} from "../utils/zoneTransformers";

export type ForecastSource = "api" | "sample_fallback" | null;

export interface ZoneDetailsResult {
  forecast: ZoneForecast | null;
  selectedZone: Zone | null;
  whyNow: WhyNowData | null;
  loading: boolean;
  apiOnline: boolean | null;
  source: ForecastSource;
  error: string | null;
}

export function useZoneDetails(
  zoneId: string | null,
  localProps: ZoneGeoJSONProperties | null
): ZoneDetailsResult {
  const [apiForecast, setApiForecast] = useState<ZoneForecast | null>(null);
  const [apiZoneRisk, setApiZoneRisk] = useState<Zone | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!zoneId) {
      setApiForecast(null);
      setApiZoneRisk(null);
      setError(null);
      setApiOnline(null);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([getZoneForecast(zoneId), getZoneRisk(zoneId)])
      .then(([forecastData, zoneRiskData]) => {
        setApiForecast(forecastData);
        setApiZoneRisk(zoneRiskData);
        setApiOnline(true);
        setLoading(false);
      })
      .catch((err: unknown) => {
        // Backend down or CORS error → fall back gracefully to local sample data.
        setApiForecast(null);
        setApiZoneRisk(null);
        setApiOnline(false);
        setError(String(err));
        setLoading(false);
      });
  }, [zoneId]);

  // If API data is available: build WhyNowData from prototype scorer contributors
  if (apiForecast && apiZoneRisk) {
    const whyNow: WhyNowData = {
      zone_id: apiZoneRisk.zone_id,
      model_type: "prototype",
      drivers: (apiZoneRisk.contributors ?? []).map((c) => ({
        feature: c.component ?? c.feature,
        display_name: c.display_name ?? c.feature,
        direction:
          c.contribution > 0.15
            ? "up"
            : c.contribution > 0.05
              ? "neutral"
              : "down",
        description: `Prototype weighted contribution: +${c.contribution.toFixed(4)} (weight: ${c.weight ?? "N/A"})`,
        freshness: "Sample",
        contribution: c.contribution,
      })),
      data_meta: apiZoneRisk.data_meta,
    };

    return {
      forecast: apiForecast,
      selectedZone: apiZoneRisk,
      whyNow,
      loading,
      apiOnline: true,
      source: "api",
      error: null,
    };
  }

  // Fall back to local transformer data
  const localForecast = localProps ? propsToForecast(localProps) : null;
  const localZone = localProps ? propsToZone(localProps) : null;
  const localWhyNow = localProps ? propsToWhyNow(localProps) : null;

  return {
    forecast: localForecast,
    selectedZone: localZone,
    whyNow: localWhyNow,
    loading,
    apiOnline,
    source: localProps ? "sample_fallback" : null,
    error,
  };
}
