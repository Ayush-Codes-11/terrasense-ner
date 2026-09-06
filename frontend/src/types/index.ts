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

export interface NormalizedFeatures {
  terrain: number;
  recent_rainfall: number;
  antecedent_rainfall: number;
  soil_wetness: number;
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
  soil_wetness_index?: number;
  normalized_features?: NormalizedFeatures;
  contributors?: Contributor[];
  feature_provenance?: Record<string, string>;
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
  observed_provenance?: string;
  forecast_provenance?: string;
  observation_timestamp?: string | null;
  observed_buckets?: Record<string, any> | null;
}

// ----- Risk Forecast (weather-linked antecedent-aware outlook) -----

export interface ForecastWindow {
  horizon?: string;
  risk: RiskLevel;
  risk_category?: string;
  risk_score: number;
  score?: number;
  antecedent_rain_mm: number;          // 3-day rolling accumulation
  recent_24h_rain_mm?: number;
  forecast_interval_rain_mm?: number | null;
  mode?: string;
  input_data_type?: string;
  score_type?: string;
  is_probability?: boolean;
  is_calibrated?: boolean;
}

export interface ZoneForecast {
  zone_id: string;
  current: RiskLevel;
  current_score: number;
  windows?: {
    now: ForecastWindow;
    "24h": ForecastWindow;
    "48h": ForecastWindow;
    "72h": ForecastWindow;
  };
  now?: ForecastWindow;
  forecast: {
    "24h": ForecastWindow;
    "48h": ForecastWindow;
    "72h": ForecastWindow;
  };
  risk_change_summary?: string;
  transition_details?: string[];
  data_meta: DataMeta;
}

// ----- Exposure (Phase 6) -----

export type FacilityType = "road" | "village" | "hospital" | "clinic" | "police" | "fire_station" | "other";

export interface ExposedFeature {
  feature_id: string;
  name: string | null;
  type: FacilityType;
  exposed: boolean;
  length_km?: number;
  /**
   * blocked is ONLY true when a verified field report confirms blockage.
   * It defaults to false even when exposed = true.
   */
  blocked: boolean;
  road_status?: string;
  verified_report_id?: string;
}

export interface ExposureSummary {
  osm_road_segments_count?: number;
  motorable_road_segments_count?: number;
  motorable_road_km?: number;
  total_road_km?: number;
  pedestrian_road_km?: number;
  track_road_km?: number;
  mapped_communities?: number;
  critical_facilities?: number;
  roads_blocked: number;
  roads_exposed: number;
  roads_exposed_km: number;
  villages_exposed: number;
  hospitals_exposed: number;
}

export interface ExposureData {
  zone_id: string;
  summary: ExposureSummary;
  roads?: Array<{
    feature_id: string;
    name: string | null;
    highway: string;
    length_km: number;
    blockage_verified: boolean;
    road_status: string;
  }>;
  settlements?: Array<{
    feature_id: string;
    name: string | null;
    place: string;
  }>;
  critical_facilities?: Array<{
    feature_id: string;
    name: string | null;
    category: string;
  }>;
  exposed_features?: ExposedFeature[];
  hazard_geometry?: string;
  exposure_features?: string;
  analysis_mode?: string;
  data_meta: DataMeta;
}

// ----- Prototype Decision-Support Priority (Phase 6) -----

export type PriorityLevel = "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH" | "MEDIUM" | "CRITICAL";

export interface HorizonPriority {
  horizon: string;
  priority: string;
  priority_score: number;
  landslide_risk_score: number;
  landslide_risk_category: string;
  score_type?: string;
  contributors?: Array<{
    component: string;
    display_name: string;
    weight: number;
    raw_value: number;
    normalized_input: number;
    contribution: number;
  }>;
}

export interface PriorityData {
  zone_id: string;
  priority: PriorityLevel;
  priority_score?: number;
  priority_label: "PROTOTYPE DECISION-SUPPORT — NOT OFFICIAL";
  windows?: {
    now: HorizonPriority;
    "24h": HorizonPriority;
    "48h": HorizonPriority;
    "72h": HorizonPriority;
  };
  now?: HorizonPriority;
  forecast?: {
    "24h": HorizonPriority;
    "48h": HorizonPriority;
    "72h": HorizonPriority;
  };
  explanation?: string;
  horizon_transitions?: string[];
  exposure_summary?: {
    roads_exposed_count: number;
    roads_exposed_km: number;
    settlements_exposed: number;
    critical_facilities_exposed: number;
    blockage_verified: boolean;
    road_status: string;
  };
  reasoning?: string[];
  hazard_geometry?: string;
  exposure_features?: string;
  analysis_mode?: string;
  data_meta: DataMeta;
}


// ----- Why Now (feature attribution) -----

export type FeatureDirection = "up" | "down" | "neutral";
export type FeatureFreshness = "Real" | "REAL DEM" | "REAL GPM" | "SAMPLE GPM" | "Sample" | "Static" | "Unavailable";

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
