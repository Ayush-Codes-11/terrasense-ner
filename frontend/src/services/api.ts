// ============================================================
// api.ts — TerraSense frontend API client
// Phase 3: real fetch calls to FastAPI backend
//
// VITE_API_BASE_URL is read from .env.development (or .env)
// If the variable is missing or the backend is down, functions
// throw — callers must handle the error and fall back to local data.
// ============================================================

import type {
  Zone,
  ZoneForecast,
  WeatherData,
  DistrictMeta,
  Alert,
  ExposureData,
  PriorityData,
} from "../types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

async function apiFetch<T>(path: string): Promise<T> {
  if (!BASE) throw new Error("VITE_API_BASE_URL is not set");
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${path}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Helpers: map backend shape → TS types ───────────────────────────────────
// The backend ZoneForecastResponse matches the frontend ZoneForecast interface
// (same field names: zone_id, current, current_score, forecast, data_meta).

// ── Zone list ────────────────────────────────────────────────────────────────

/** Returns all zones' current risk from /risk/current */
export async function getAllZoneRisks(): Promise<Zone[]> {
  const data = await apiFetch<{
    zones: Array<{
      zone_id: string;
      risk_category: string;
      risk_score: number;
      score?: number;
      score_type?: string;
      is_probability?: boolean;
      is_calibrated?: boolean;
      computed_by?: string;
      slope: number;
      elevation: number;
      soil_moisture: number;
      soil_wetness_index?: number;
      normalized_features?: Zone["normalized_features"];
      contributors?: Zone["contributors"];
      feature_provenance?: Record<string, string>;
      data_meta: Zone["data_meta"];
    }>;
  }>("/risk/current");

  return data.zones.map((z) => ({
    zone_id: z.zone_id,
    risk: z.risk_category as Zone["risk"],
    risk_score: z.score ?? z.risk_score,
    score: z.score ?? z.risk_score,
    score_type: z.score_type,
    is_probability: z.is_probability,
    is_calibrated: z.is_calibrated,
    computed_by: z.computed_by,
    slope_deg: z.slope,
    elevation_m: z.elevation,
    soil_moisture_index: z.soil_wetness_index ?? z.soil_moisture,
    soil_wetness_index: z.soil_wetness_index ?? z.soil_moisture,
    normalized_features: z.normalized_features,
    contributors: z.contributors,
    feature_provenance: z.feature_provenance,
    data_meta: z.data_meta,
  }));
}

// ── Single zone risk ─────────────────────────────────────────────────────────

export async function getZoneRisk(zoneId: string): Promise<Zone> {
  const z = await apiFetch<{
    zone_id: string;
    risk_category: string;
    risk_score: number;
    score?: number;
    score_type?: string;
    is_probability?: boolean;
    is_calibrated?: boolean;
    computed_by?: string;
    slope: number;
    elevation: number;
    soil_moisture: number;
    soil_wetness_index?: number;
    normalized_features?: Zone["normalized_features"];
    contributors?: Zone["contributors"];
    feature_provenance?: Record<string, string>;
    data_meta: Zone["data_meta"];
  }>(`/risk/current/${encodeURIComponent(zoneId)}`);

  return {
    zone_id: z.zone_id,
    risk: z.risk_category as Zone["risk"],
    risk_score: z.score ?? z.risk_score,
    score: z.score ?? z.risk_score,
    score_type: z.score_type,
    is_probability: z.is_probability,
    is_calibrated: z.is_calibrated,
    computed_by: z.computed_by,
    slope_deg: z.slope,
    elevation_m: z.elevation,
    soil_moisture_index: z.soil_wetness_index ?? z.soil_moisture,
    soil_wetness_index: z.soil_wetness_index ?? z.soil_moisture,
    normalized_features: z.normalized_features,
    contributors: z.contributors,
    feature_provenance: z.feature_provenance,
    data_meta: z.data_meta,
  };
}

// ── Zone forecast ─────────────────────────────────────────────────────────────

/**
 * Fetches NOW + 24h/48h/72h forecast for a zone.
 * Response shape matches the TypeScript ZoneForecast interface directly.
 */
export async function getZoneForecast(zoneId: string): Promise<ZoneForecast> {
  return apiFetch<ZoneForecast>(
    `/risk/forecast/${encodeURIComponent(zoneId)}`
  );
}

// ── Weather ───────────────────────────────────────────────────────────────────

export async function getZoneWeather(zoneId: string): Promise<WeatherData> {
  const w = await apiFetch<{
    zone_id: string;
    observed_daily_mm?: { d_minus_2: number; d_minus_1: number; d0: number };
    forecast_interval_mm?: { "0_24h": number; "24_48h": number; "48_72h": number };
    rolling_3d_accumulation_mm?: { now: number; "24h": number; "48h": number; "72h": number };
    recent_24h_mm?: { now: number; "24h": number; "48h": number; "72h": number };
    rain_24h_mm?: number;
    rain_3d_mm?: number;
    forecast_24h_mm?: number;
    forecast_48h_mm?: number;
    forecast_72h_mm?: number;
    observed_provenance?: string;
    forecast_provenance?: string;
    observation_timestamp?: string | null;
    observed_buckets?: Record<string, any> | null;
    data_meta: WeatherData["data_meta"];
  }>(`/weather/${encodeURIComponent(zoneId)}`);

  const rain24 = w.recent_24h_mm?.now ?? w.observed_daily_mm?.d0 ?? w.rain_24h_mm ?? 0;
  const rain3d = w.rolling_3d_accumulation_mm?.now ?? w.rain_3d_mm ?? 0;
  const f24 = w.forecast_interval_mm?.["0_24h"] ?? w.forecast_24h_mm ?? 0;
  const f48 = w.forecast_interval_mm?.["24_48h"] ?? w.forecast_48h_mm ?? 0;
  const f72 = w.forecast_interval_mm?.["48_72h"] ?? w.forecast_72h_mm ?? 0;

  return {
    zone_id: w.zone_id,
    rain_1h_mm: null,
    rain_6h_mm: null,
    rain_24h_mm: rain24,
    rain_3d_mm: rain3d,
    forecast_0_24h_mm: f24,
    forecast_24_48h_mm: f48,
    forecast_48_72h_mm: f72,
    observed_provenance: w.observed_provenance,
    forecast_provenance: w.forecast_provenance,
    observation_timestamp: w.observation_timestamp,
    observed_buckets: w.observed_buckets,
    data_meta: w.data_meta,
  };
}

export async function getWeatherStatus(): Promise<Record<string, any>> {
  return apiFetch<Record<string, any>>("/weather/status");
}

/** Returns the truthful Phase 7-10 connectivity, source, and verification state. */
export async function getOperationsStatus(): Promise<Record<string, any>> {
  return apiFetch<Record<string, any>>("/operations/status");
}

// ── District meta (Phase 5+) ──────────────────────────────────────────────────

export async function getDistrictMeta(): Promise<DistrictMeta | null> {
  // Not implemented in backend yet — return null gracefully.
  return null;
}

// ── Alerts (Phase 10+) ────────────────────────────────────────────────────────

export async function getAlerts(): Promise<Alert[]> {
  // Not implemented in backend yet.
  return [];
}

// ── Exposure & Priority (Phase 6) ─────────────────────────────────────────────

export async function getZoneExposure(zoneId: string): Promise<ExposureData> {
  return apiFetch<ExposureData>(`/exposure/${encodeURIComponent(zoneId)}`);
}

export async function getZonePriority(zoneId: string): Promise<PriorityData> {
  return apiFetch<PriorityData>(`/priority/${encodeURIComponent(zoneId)}`);
}

export async function getOsmStatus(): Promise<{
  status: string;
  is_real: boolean;
  retrieved_at: string | null;
  source: string;
  attribution: string;
  feature_counts: Record<string, number>;
}> {
  return apiFetch(`/geodata/osm/status`);
}

// ── Field Reports (Phase 9) ───────────────────────────────────────────────────

export async function submitFieldReport(report: any): Promise<any> {
  if (!BASE) throw new Error("VITE_API_BASE_URL is not set");
  const res = await fetch(`${BASE}/field-reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(report),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status} /field-reports: ${body}`);
  }
  return res.json();
}
