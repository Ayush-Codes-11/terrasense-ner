// ============================================================
// GeoJSON property types for sample data layer
// Matches the schema in data/sample/grid-risk.geojson exactly.
// ============================================================

export interface ZoneGeoJSONProperties {
  zone_id: string;
  risk_category: string; // "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH"
  risk_score: number;    // 0.0 – 1.0
  slope: number;         // degrees
  elevation: number;     // metres
  soil_moisture: number; // 0.0 – 1.0 index
  rain_24h: number;      // mm observed, past 24h
  rain_3d: number;       // mm observed, past 3 days
  rain_7d: number;       // mm observed, past 7 days
  forecast_24h: number;  // mm forecast, next 0→24h window
  forecast_48h: number;  // mm forecast, next 24→48h window
  forecast_72h: number;  // mm forecast, next 48→72h window
  // Antecedent (accumulated) totals — pre-computed in sample data.
  // antecedent_Nh = observed_24h + sum of all forecast windows up to N hours.
  antecedent_24h: number;
  antecedent_48h: number;
  antecedent_72h: number;
  forecast_risk_24h: string;
  forecast_risk_48h: string;
  forecast_risk_72h: string;
  forecast_score_24h: number;
  forecast_score_48h: number;
  forecast_score_72h: number;
  data_type: "SAMPLE_MOCK";
}

export interface RoadGeoJSONProperties {
  road_id: string;
  name: string;
  road_type: "national_highway" | "state_highway" | "district_road" | "local_road";
  data_type: "SAMPLE_MOCK";
}

export interface VillageGeoJSONProperties {
  village_id: string;
  name: string;
  population_est: number;
  zone_id: string;
  data_type: "SAMPLE_MOCK";
}

export interface FacilityGeoJSONProperties {
  facility_id: string;
  name: string;
  facility_type: "hospital" | "primary_health_centre" | "emergency_centre" | "other";
  zone_id: string;
  data_type: "SAMPLE_MOCK";
}
