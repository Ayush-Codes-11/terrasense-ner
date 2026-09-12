import type { FeatureCollection, Geometry } from "geojson";

export interface StateInfo { state_id: string; state_name: string; region_id: string }
export interface DistrictInfo { district_id: string; district_name: string; state_id: string; coverage_level: string; risk_model_status: string; lgd_code: string | null }
export interface ZoneInfo { zone_id: string; district_id: string; zone_type: string }
export type MapProperties = Partial<StateInfo & DistrictInfo & ZoneInfo>;
export type Boundaries = FeatureCollection<Geometry, MapProperties> & { count?: number; boundary_vintage?: string };
export interface ZoneList { count: number; items: ZoneInfo[]; detailed_zone_model_available: boolean }
export interface RiskRecord {
  zone_id: string; risk_score: number; risk_category: string; slope?: number; elevation?: number;
  rain_24h?: number; rain_3d?: number; normalized_features?: { soil_wetness?: number };
  contributors?: { feature: string; display_name?: string; contribution: number }[];
  feature_provenance?: Record<string, string>;
}
export interface WeatherContext {
  forecast_interval_mm?: Record<string, number>; observation_timestamp?: string;
  observed_provenance?: string; forecast_provenance?: string;
  data_meta?: { note?: string; is_live?: boolean };
}
export class SpatialError extends Error {
  status: number;
  constructor(status: number) { super(status === 404 ? "This geographic selection was not found." : "Spatial data is temporarily unavailable."); this.status = status; }
}
const cache = new Map<string, { expires: number; promise: Promise<unknown> }>();
export function clearSpatialCache() { cache.clear(); }
export function spatialFetch<T>(path: string, ttl = 300_000): Promise<T> {
  const cached = cache.get(path);
  if (cached && cached.expires > Date.now()) return cached.promise as Promise<T>;
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  const promise = (async () => {
    try {
      if (!base) throw new SpatialError(503);
      const response = await fetch(base + path, { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new SpatialError(response.status);
      return await response.json() as T;
    } catch (error) { cache.delete(path); throw error instanceof SpatialError ? error : new SpatialError(503); }
  })();
  cache.set(path, { expires: Date.now() + ttl, promise });
  return promise;
}
