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
      contributors?: Zone["contributors"];
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
    soil_moisture_index: z.soil_moisture,
    contributors: z.contributors,
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
    contributors?: Zone["contributors"];
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
    soil_moisture_index: z.soil_moisture,
    contributors: z.contributors,
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
    rain_24h_mm: number;
    rain_3d_mm: number;
    rain_7d_mm: number;
    forecast_24h_mm: number;
    forecast_48h_mm: number;
    forecast_72h_mm: number;
    data_meta: WeatherData["data_meta"];
  }>(`/weather/${encodeURIComponent(zoneId)}`);

  return {
    zone_id: w.zone_id,
    rain_1h_mm: null,
    rain_6h_mm: null,
    rain_24h_mm: w.rain_24h_mm,
    rain_3d_mm: w.rain_3d_mm,
    forecast_0_24h_mm: w.forecast_24h_mm,
    forecast_24_48h_mm: w.forecast_48h_mm,
    forecast_48_72h_mm: w.forecast_72h_mm,
    data_meta: w.data_meta,
  };
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
