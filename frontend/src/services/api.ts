// ============================================================
// TerraSense NER — API Service Layer (stub)
// Phase 1: Stub only. All functions return null.
// Phase 3+: Replace stubs with real axios calls to FastAPI.
// ============================================================

import type {
  Zone,
  ZoneForecast,
  ExposureData,
  PriorityData,
  WhyNowData,
  WeatherData,
  FieldReport,
  ReportSubmission,
  Alert,
  DistrictMeta,
} from "../types";

// Base URL will be read from env in Phase 3
// const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ---- District metadata ----

export async function getDistrictMeta(): Promise<DistrictMeta | null> {
  // Phase 3: GET /district
  return null;
}

// ---- Zones ----

export async function getAllZones(): Promise<Zone[]> {
  // Phase 3: GET /zones
  return [];
}

// ---- Risk ----

export async function getCurrentRisk(): Promise<Zone[]> {
  // Phase 3: GET /risk/current
  return [];
}

export async function getZoneForecast(
  zoneId: string
): Promise<ZoneForecast | null> {
  // Phase 3: GET /risk/forecast/{zone_id}
  void zoneId;
  return null;
}

// ---- Weather ----

export async function getWeather(zoneId: string): Promise<WeatherData | null> {
  // Phase 3: GET /weather/{zone_id}
  void zoneId;
  return null;
}

// ---- Exposure ----

export async function getExposure(
  zoneId: string
): Promise<ExposureData | null> {
  // Phase 3: GET /exposure/{zone_id}
  void zoneId;
  return null;
}

// ---- Priority ----

export async function getPriority(
  zoneId: string
): Promise<PriorityData | null> {
  // Phase 3: GET /priority/{zone_id}
  void zoneId;
  return null;
}

// ---- Why Now ----

export async function getWhyNow(zoneId: string): Promise<WhyNowData | null> {
  // Phase 3: GET /why-now/{zone_id}
  void zoneId;
  return null;
}

// ---- Field Reports ----

export async function submitReport(
  report: ReportSubmission
): Promise<FieldReport | null> {
  // Phase 8: POST /reports
  void report;
  return null;
}

export async function getReports(): Promise<FieldReport[]> {
  // Phase 8: GET /reports
  return [];
}

// ---- Alerts ----

export async function getAlerts(): Promise<Alert[]> {
  // Phase 10: GET /alerts
  return [];
}
