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
export interface SpatialDataMeta {
  data_type: string;
  source: string;
  timestamp?: string;
  is_live: boolean;
  note?: string;
  attribution?: string;
  is_raw?: boolean;
  count?: number;
}
export interface ExposedRoad {
  feature_id: string;
  name: string | null;
  highway: string;
  length_km: number;
  is_motorable: boolean;
  access: string | null;
  access_restricted: boolean;
  blockage_verified: boolean;
  road_status: string;
}
export interface ExposedSettlement {
  feature_id: string;
  name: string | null;
  place: string;
  community_id: string | null;
}
export interface ExposedFacility {
  feature_id: string;
  name: string | null;
  category: string;
  amenity: string | null;
  healthcare: string | null;
  is_whitelisted: boolean;
}
export interface ExposureSummary {
  osm_road_segments_count: number;
  motorable_road_segments_count: number;
  motorable_road_km: number;
  total_road_km: number;
  pedestrian_road_km: number;
  track_road_km: number;
  mapped_communities: number;
  critical_facilities: number;
  roads_blocked: number;
  roads_exposed: number;
  roads_exposed_km: number;
  villages_exposed: number;
  hospitals_exposed: number;
}
export interface ZoneExposure {
  zone_id: string;
  summary: ExposureSummary;
  roads: ExposedRoad[];
  settlements: ExposedSettlement[];
  critical_facilities: ExposedFacility[];
  hazard_geometry: string;
  exposure_features: string;
  analysis_mode: string;
  data_meta: SpatialDataMeta;
}
export interface OperationalFeatureProperties {
  osm_id?: string | number;
  facility_id?: string | number;
  road_id?: string | number;
  name?: string | null;
  category?: string | null;
  facility_type?: string | null;
  amenity?: string | null;
  healthcare?: string | null;
  highway?: string | null;
  road_type?: string | null;
  source?: string | null;
  data_type?: string | null;
  [key: string]: unknown;
}
export type OperationalFeatureCollection = FeatureCollection<Geometry, OperationalFeatureProperties> & { data_meta: SpatialDataMeta };
export interface OSMStatus {
  status: "OSM snapshot" | "Cached OSM" | "Sample fallback";
  is_real: boolean;
  retrieved_at: string | null;
  layers_retrieved_at?: Record<string, string> | null;
  dataset_description?: string | null;
  source: string;
  attribution: string;
  feature_counts: Record<string, number>;
  data_meta: SpatialDataMeta;
}
export class SpatialError extends Error {
  status: number;
  constructor(status: number) { super(status === 404 ? "This geographic selection was not found." : "Spatial data is temporarily unavailable."); this.status = status; }
}
const cache = new Map<string, { expires: number; promise: Promise<unknown> }>();
export function clearSpatialCache() { cache.clear(); }
const apiBase = () => (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function spatialRequest<T>(path: string, signal?: AbortSignal): Promise<T> {
  const base = apiBase();
  try {
    if (!base) throw new SpatialError(503);
    const response = await fetch(base + path, { headers: { Accept: "application/json" }, signal: signal ?? AbortSignal.timeout(15000) });
    if (!response.ok) throw new SpatialError(response.status);
    return await response.json() as T;
  } catch (error) {
    if (signal?.aborted) throw error;
    throw error instanceof SpatialError ? error : new SpatialError(503);
  }
}

export function spatialFetch<T>(path: string, ttl = 300_000): Promise<T> {
  const cached = cache.get(path);
  if (cached && cached.expires > Date.now()) return cached.promise as Promise<T>;
  const promise = (async () => {
    try { return await spatialRequest<T>(path); }
    catch (error) { cache.delete(path); throw error; }
  })();
  cache.set(path, { expires: Date.now() + ttl, promise });
  return promise;
}

export function fetchZoneExposure(zoneId: string, signal: AbortSignal): Promise<ZoneExposure> {
  return spatialRequest<ZoneExposure>(`/exposure/${encodeURIComponent(zoneId)}`, signal);
}

function withSampleMeta(data: FeatureCollection<Geometry, OperationalFeatureProperties>, note: string): OperationalFeatureCollection {
  return {
    ...data,
    data_meta: {
      data_type: "SAMPLE_MOCK",
      source: "TerraSense sample fallback",
      is_live: false,
      attribution: "Sample fallback",
      note,
    },
  };
}

async function sampleOperationalLayer(path: string, note: string, signal: AbortSignal): Promise<OperationalFeatureCollection> {
  const response = await fetch(path, { headers: { Accept: "application/json" }, signal });
  if (!response.ok) throw new SpatialError(response.status);
  return withSampleMeta(await response.json() as FeatureCollection<Geometry, OperationalFeatureProperties>, note);
}

export async function fetchOperationalRoads(signal: AbortSignal): Promise<OperationalFeatureCollection> {
  try {
    return await spatialRequest<OperationalFeatureCollection>("/geodata/osm/roads", signal);
  } catch (error) {
    if (signal.aborted) throw error;
    return sampleOperationalLayer("/data/sample/roads.geojson", "Fictitious sample road geometry for interface testing only.", signal);
  }
}

export async function fetchOperationalFacilities(signal: AbortSignal): Promise<OperationalFeatureCollection> {
  try {
    return await spatialRequest<OperationalFeatureCollection>("/geodata/osm/critical-facilities", signal);
  } catch (error) {
    if (signal.aborted) throw error;
    return sampleOperationalLayer("/data/sample/hospitals.geojson", "Fictitious sample facilities for interface testing only.", signal);
  }
}

export function fetchOsmStatus(signal: AbortSignal): Promise<OSMStatus> {
  return spatialRequest<OSMStatus>("/geodata/osm/status", signal);
}
