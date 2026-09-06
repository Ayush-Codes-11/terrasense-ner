// ============================================================
// TerraSense NER — Shared TypeScript Types & Interfaces
// Phase 1: Shell definitions — ready for real API data later
// ============================================================

// ----- Risk classification -----

export type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH";

export type DataSource = "real" | "sample" | "unavailable";

export interface DataMeta {
  source: DataSource;
  freshness: string | null; // ISO-8601 timestamp or null
  note?: string;
  data_type?: string;   // optional: "SAMPLE_MOCK" when backend includes it
  is_live?: boolean;    // optional: false for sample responses
}

export interface Contributor {
  feature: string;
  contribution: number;
  component?: string;
  display_name?: string;
  normalized_input?: number;
  weight?: number;
}

export interface Zone {
  zone_id: string;
  name?: string;
  risk: RiskLevel;
  risk_score: number; // 0.0 – 1.0
  score?: number;
  score_type?: string;
  is_probability?: boolean;
  is_calibrated?: boolean;
  computed_by?: string;
  slope_deg?: number;
  elevation_m?: number;
  soil_moisture_index?: number;
  contributors?: Contributor[];
  data_meta: DataMeta;
}

// ----- Weather / Rainfall -----

export interface RainfallWindow {
  rain_1h_mm: number | null;
  rain_6h_mm: number | null;
  rain_24h_mm: number | null;
  rain_3d_mm: number | null;
}

export interface RainfallForecast {
  forecast_0_24h_mm: number | null;
  forecast_24_48h_mm: number | null;
  forecast_48_72h_mm: number | null;
}

export interface WeatherData extends RainfallWindow, RainfallForecast {
  zone_id: string;
  data_meta: DataMeta;
}

// ----- Risk Forecast (antecedent-aware) -----

export interface ForecastWindow {
  risk: RiskLevel;
  risk_score: number;
  antecedent_rain_mm: number; // accumulated observed + forecast
}

export interface ZoneForecast {
  zone_id: string;
  current: RiskLevel;
  current_score: number;
  forecast: {
    "24h": ForecastWindow;
    "48h": ForecastWindow;
    "72h": ForecastWindow;
  };
  data_meta: DataMeta;
}

// ----- Exposure -----

export type FacilityType = "road" | "village" | "hospital" | "other";

export interface ExposedFeature {
  feature_id: string;
  name: string;
  type: FacilityType;
  exposed: boolean;
  /**
   * blocked is ONLY true when a verified field report confirms blockage.
   * It defaults to false even when exposed = true.
   */
  blocked: boolean;
  verified_report_id?: string;
}

export interface ExposureData {
  zone_id: string;
  exposed_features: ExposedFeature[];
  summary: {
    roads_exposed: number;
    villages_exposed: number;
    hospitals_exposed: number;
    roads_blocked: number; // verified field reports only
  };
  data_meta: DataMeta;
}

// ----- Prototype Decision-Support Priority -----

export type PriorityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface PriorityData {
  zone_id: string;
  priority: PriorityLevel;
  /**
   * Always displayed. This is NOT an official government classification.
   */
  priority_label: "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL";
  reasoning: string[];
  data_meta: DataMeta;
}

// ----- Why Now (feature attribution) -----

export type FeatureDirection = "up" | "down" | "neutral";
export type FeatureFreshness = "Real" | "Sample" | "Static" | "Unavailable";

export interface FeatureDriver {
  feature: string;
  display_name: string;
  direction: FeatureDirection;
  description: string;
  freshness: FeatureFreshness;
  contribution?: number;
}

export interface WhyNowData {
  zone_id: string;
  model_type: "sample" | "prototype" | "xgboost";
  drivers: FeatureDriver[]; // top 3–4
  data_meta: DataMeta;
}

// ----- Field Reports -----

export type ReportType =
  | "slope_crack"
  | "debris"
  | "road_blockage"
  | "landslide"
  | "other";

export interface ReportSubmission {
  report_type: ReportType;
  description: string;
  latitude: number | null;
  longitude: number | null;
  photo_base64?: string; // Phase 8+
  blocked_road: boolean;
  offline?: boolean; // set by client when saved to IndexedDB
}

export interface FieldReport extends ReportSubmission {
  report_id: string;
  submitted_at: string; // ISO-8601
  verified: boolean;
  zone_id?: string;
  sync_status?: "synced" | "pending" | "failed";
}

// ----- Alerts -----

export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";

export interface Alert {
  alert_id: string;
  zone_id: string;
  severity: AlertSeverity;
  message: string;
  previous_risk?: RiskLevel;
  current_risk: RiskLevel;
  created_at: string; // ISO-8601
  acknowledged: boolean;
}

// ----- Dashboard state -----

export interface DistrictMeta {
  district_name: string;
  state: string;
  pilot: boolean;
  last_updated: string | null; // ISO-8601
  data_mode: "sample" | "mixed" | "real";
}
