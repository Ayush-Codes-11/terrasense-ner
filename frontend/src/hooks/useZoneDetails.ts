// ============================================================
// useZoneDetails — fetches zone forecast, risk, exposure, and priority from FastAPI.
// Falls back to local GeoJSON-derived data if the backend is down.
//
// source = "api"             → data from FastAPI endpoints
// source = "sample_fallback" → data derived locally via zoneTransformers
// source = null              → no zone selected
// ============================================================

import { useState, useEffect } from "react";
import type { Zone, ZoneForecast, WhyNowData, ExposureData, PriorityData, FeatureFreshness } from "../types";
import type { ZoneGeoJSONProperties } from "../types/geojson";
import {
  getZoneForecast,
  getZoneRisk,
  getZoneExposure,
  getZonePriority,
} from "../services/api";
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
  exposure: ExposureData | null;
  priority: PriorityData | null;
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
  const [apiExposure, setApiExposure] = useState<ExposureData | null>(null);
  const [apiPriority, setApiPriority] = useState<PriorityData | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!zoneId) {
      setApiForecast(null);
      setApiZoneRisk(null);
      setApiExposure(null);
      setApiPriority(null);
      setError(null);
      setApiOnline(null);
      return;
    }

    setLoading(true);
    setError(null);

    Promise.all([
      getZoneForecast(zoneId),
      getZoneRisk(zoneId),
      getZoneExposure(zoneId),
      getZonePriority(zoneId),
    ])
      .then(([forecastData, zoneRiskData, exposureData, priorityData]) => {
        setApiForecast(forecastData);
        setApiZoneRisk(zoneRiskData);
        setApiExposure(exposureData);
        setApiPriority(priorityData);
        setApiOnline(true);
        setLoading(false);
      })
      .catch((err: unknown) => {
        // Backend down or CORS error → fall back gracefully to local sample data.
        setApiForecast(null);
        setApiZoneRisk(null);
        setApiExposure(null);
        setApiPriority(null);
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
      drivers: (apiZoneRisk.contributors ?? []).map((c) => {
        const isTerrain =
          c.component === "terrain" ||
          (c.display_name && c.display_name.toLowerCase().includes("terrain")) ||
          c.feature.toLowerCase().includes("slope");

        const isRecentRain =
          c.component === "recent_rainfall" ||
          (c.display_name && c.display_name.toLowerCase().includes("recent")) ||
          c.feature.toLowerCase().includes("24h");

        const isAntecedentRain =
          c.component === "antecedent_rainfall" ||
          (c.display_name && c.display_name.toLowerCase().includes("antecedent")) ||
          c.feature.toLowerCase().includes("3d");

        const hasRealGpm =
          apiZoneRisk.feature_provenance?.observed_rainfall === "REAL_GPM" ||
          apiZoneRisk.feature_provenance?.rainfall === "REAL_GPM";

        const isObservedRain = (isRecentRain || isAntecedentRain) && hasRealGpm;

        const slopeVal =
          apiZoneRisk.slope_deg !== undefined
            ? apiZoneRisk.slope_deg.toFixed(2)
            : "";

        let freshness: FeatureFreshness = "Sample";
        let description = `Prototype weighted contribution: +${c.contribution.toFixed(4)} (weight: ${c.weight ?? "N/A"})`;

        if (isTerrain) {
          freshness = "REAL DEM";
          description = `Terrain slope: ${slopeVal}° mean — real Copernicus GLO-30 DEM`;
        } else if (isObservedRain) {
          freshness = "REAL GPM";
          description = isRecentRain
            ? `Recent 24h rainfall: observed NASA GPM IMERG Late (~0.1° grid)`
            : `3-day antecedent rainfall: observed NASA GPM IMERG Late (~0.1° grid)`;
        }

        return {
          feature: c.component ?? c.feature,
          display_name: isTerrain
            ? "Terrain slope"
            : isRecentRain
              ? "Recent 24h rainfall (observed)"
              : isAntecedentRain
                ? "3-day antecedent rainfall (observed)"
                : (c.display_name ?? c.feature),
          direction:
            c.contribution > 0.15
              ? "up"
              : c.contribution > 0.05
                ? "neutral"
                : "down",
          description,
          freshness,
          contribution: c.contribution,
        };
      }),
      data_meta: apiZoneRisk.data_meta,
    };

    return {
      forecast: apiForecast,
      selectedZone: apiZoneRisk,
      whyNow,
      exposure: apiExposure,
      priority: apiPriority,
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
  const localExposure: ExposureData | null = localProps
    ? {
        zone_id: localProps.zone_id,
        summary: {
          roads_exposed: 2,
          roads_exposed_km: 1.5,
          villages_exposed: 1,
          hospitals_exposed: 1,
          roads_blocked: 0,
        },
        data_meta: {
          data_type: "SAMPLE_MOCK",
          source: "sample",
          freshness: null,
          is_live: false,
          note: "Sample fallback — backend offline",
        },
      }
    : null;

  const localPriority: PriorityData | null = localProps
    ? {
        zone_id: localProps.zone_id,
        priority:
          localProps.risk_category === "VERY_HIGH"
            ? "VERY_HIGH"
            : localProps.risk_category === "HIGH"
              ? "HIGH"
              : "MODERATE",
        priority_label: "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL",
        explanation: `Sample fallback priority for Zone ${localProps.zone_id}.`,
        data_meta: {
          data_type: "SAMPLE_MOCK",
          source: "sample",
          freshness: null,
          is_live: false,
          note: "Sample fallback — backend offline",
        },
      }
    : null;

  return {
    forecast: localForecast,
    selectedZone: localZone,
    whyNow: localWhyNow,
    exposure: localExposure,
    priority: localPriority,
    loading,
    apiOnline,
    source: localProps ? "sample_fallback" : null,
    error,
  };
}
