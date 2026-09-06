// ============================================================
// zoneTransformers — convert GeoJSON zone properties → card types
// All outputs carry data_meta.source = "sample" explicitly.
// No fabricated values — all data comes directly from the zone properties.
// ============================================================

import type { ZoneGeoJSONProperties } from "../types/geojson";
import type {
  Zone,
  ZoneForecast,
  WhyNowData,
  FeatureDriver,
  RiskLevel,
} from "../types";

const SAMPLE_META = {
  source: "sample" as const,
  freshness: null,
  note: "SAMPLE_MOCK — not real sensor data",
};

// ---- Zone (for RiskSeverityCard) ----

export function propsToZone(props: ZoneGeoJSONProperties): Zone {
  return {
    zone_id: props.zone_id,
    risk: props.risk_category as RiskLevel,
    risk_score: props.risk_score,
    slope_deg: props.slope,
    elevation_m: props.elevation,
    soil_moisture_index: props.soil_moisture,
    data_meta: SAMPLE_META,
  };
}

// ---- ZoneForecast (for ForecastCard) ----
// antecedent_Nh values come pre-computed in the sample data and represent
// the accumulated rainfall total (observed + summed forecast windows).
// Phase 4 backend will compute these dynamically from the rainfall accumulator.

export function propsToForecast(props: ZoneGeoJSONProperties): ZoneForecast {
  return {
    zone_id: props.zone_id,
    current: props.risk_category as RiskLevel,
    current_score: props.risk_score,
    forecast: {
      "24h": {
        risk: props.forecast_risk_24h as RiskLevel,
        risk_score: props.forecast_score_24h,
        antecedent_rain_mm: props.antecedent_24h,
      },
      "48h": {
        risk: props.forecast_risk_48h as RiskLevel,
        risk_score: props.forecast_score_48h,
        antecedent_rain_mm: props.antecedent_48h,
      },
      "72h": {
        risk: props.forecast_risk_72h as RiskLevel,
        risk_score: props.forecast_score_72h,
        antecedent_rain_mm: props.antecedent_72h,
      },
    },
    data_meta: {
      source: "sample",
      freshness: null,
      note: "SAMPLE_MOCK — antecedent rainfall pre-computed, not from real accumulator",
    },
  };
}

// ---- WhyNowData (for WhyNowCard) ----
// Drivers are derived from the zone's property values using threshold logic.
// This mimics what the Phase 7 why-now engine will produce from the prototype scorer.
// No fabricated values — every description cites the actual prop value.

export function propsToWhyNow(props: ZoneGeoJSONProperties): WhyNowData {
  const drivers: FeatureDriver[] = [];

  // 3-day rainfall
  if (props.rain_3d > 60) {
    drivers.push({
      feature: "rain_3d",
      display_name: "3-day rainfall accumulation",
      direction: "up",
      description: `${props.rain_3d}mm over past 3 days — elevated slope saturation`,
      freshness: "Sample",
    });
  } else if (props.rain_3d > 25) {
    drivers.push({
      feature: "rain_3d",
      display_name: "3-day rainfall accumulation",
      direction: "neutral",
      description: `${props.rain_3d}mm over past 3 days`,
      freshness: "Sample",
    });
  } else {
    drivers.push({
      feature: "rain_3d",
      display_name: "3-day rainfall accumulation",
      direction: "down",
      description: `${props.rain_3d}mm over past 3 days — below saturation threshold`,
      freshness: "Sample",
    });
  }

  // Slope
  if (props.slope > 32) {
    drivers.push({
      feature: "slope",
      display_name: "Terrain slope angle",
      direction: "up",
      description: `${props.slope}° — above 30° high-susceptibility threshold`,
      freshness: "Static",
    });
  } else if (props.slope > 20) {
    drivers.push({
      feature: "slope",
      display_name: "Terrain slope angle",
      direction: "neutral",
      description: `${props.slope}° — moderate gradient`,
      freshness: "Static",
    });
  } else {
    drivers.push({
      feature: "slope",
      display_name: "Terrain slope angle",
      direction: "down",
      description: `${props.slope}° — gentle gradient, lower susceptibility`,
      freshness: "Static",
    });
  }

  // Soil moisture
  if (props.soil_moisture > 0.5) {
    drivers.push({
      feature: "soil_moisture",
      display_name: "Soil moisture index",
      direction: "up",
      description: `${(props.soil_moisture * 100).toFixed(0)}% — near saturation`,
      freshness: "Sample",
    });
  } else if (props.soil_moisture > 0.33) {
    drivers.push({
      feature: "soil_moisture",
      display_name: "Soil moisture index",
      direction: "neutral",
      description: `${(props.soil_moisture * 100).toFixed(0)}% — moderate`,
      freshness: "Sample",
    });
  }

  // Forecast 24h rain
  if (props.forecast_24h > 35) {
    drivers.push({
      feature: "forecast_24h",
      display_name: "24h rainfall forecast",
      direction: "up",
      description: `${props.forecast_24h}mm expected — will significantly raise accumulated total`,
      freshness: "Sample",
    });
  } else if (props.forecast_24h > 15) {
    drivers.push({
      feature: "forecast_24h",
      display_name: "24h rainfall forecast",
      direction: "neutral",
      description: `${props.forecast_24h}mm expected in next 24h`,
      freshness: "Sample",
    });
  }

  return {
    zone_id: props.zone_id,
    model_type: "prototype",
    drivers: drivers.slice(0, 4),
    data_meta: {
      source: "sample",
      freshness: null,
      note: "SAMPLE_MOCK — threshold-derived attribution, not real SHAP values",
    },
  };
}
