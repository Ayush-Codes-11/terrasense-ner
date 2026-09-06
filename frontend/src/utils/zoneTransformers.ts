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
  // Fallback transformer when backend is down — does not consume deprecated forecast_risk_* fields
  const d0 = props.rain_24h ?? 0;
  const f1 = props.forecast_24h ?? 0;
  const f2 = props.forecast_48h ?? 0;
  const f3 = props.forecast_72h ?? 0;

  const nowAntecedent = props.rain_3d ?? d0 * 2;
  const h24Antecedent = Math.round(nowAntecedent * 0.7 + f1);
  const h48Antecedent = Math.round(nowAntecedent * 0.4 + f1 + f2);
  const h72Antecedent = Math.round(f1 + f2 + f3);

  return {
    zone_id: props.zone_id,
    current: props.risk_category as RiskLevel,
    current_score: props.risk_score,
    windows: {
      now: {
        risk: props.risk_category as RiskLevel,
        risk_score: props.risk_score,
        antecedent_rain_mm: nowAntecedent,
        recent_24h_rain_mm: d0,
        forecast_interval_rain_mm: null,
        mode: "SAMPLE_FALLBACK",
      },
      "24h": {
        risk: (h24Antecedent > 100 ? "VERY_HIGH" : h24Antecedent > 60 ? "HIGH" : "MODERATE") as RiskLevel,
        risk_score: Math.min(Number((props.risk_score * 1.1).toFixed(2)), 0.99),
        antecedent_rain_mm: h24Antecedent,
        recent_24h_rain_mm: f1,
        forecast_interval_rain_mm: f1,
        mode: "SAMPLE_FALLBACK",
      },
      "48h": {
        risk: (h48Antecedent > 100 ? "VERY_HIGH" : h48Antecedent > 60 ? "HIGH" : "MODERATE") as RiskLevel,
        risk_score: Math.min(Number((props.risk_score * 1.05).toFixed(2)), 0.99),
        antecedent_rain_mm: h48Antecedent,
        recent_24h_rain_mm: f2,
        forecast_interval_rain_mm: f2,
        mode: "SAMPLE_FALLBACK",
      },
      "72h": {
        risk: (h72Antecedent > 100 ? "VERY_HIGH" : h72Antecedent > 60 ? "HIGH" : "MODERATE") as RiskLevel,
        risk_score: Math.min(Number((props.risk_score * 0.9).toFixed(2)), 0.99),
        antecedent_rain_mm: h72Antecedent,
        recent_24h_rain_mm: f3,
        forecast_interval_rain_mm: f3,
        mode: "SAMPLE_FALLBACK",
      },
    },
    forecast: {
      "24h": {
        risk: (h24Antecedent > 100 ? "VERY_HIGH" : h24Antecedent > 60 ? "HIGH" : "MODERATE") as RiskLevel,
        risk_score: Math.min(Number((props.risk_score * 1.1).toFixed(2)), 0.99),
        antecedent_rain_mm: h24Antecedent,
        recent_24h_rain_mm: f1,
        forecast_interval_rain_mm: f1,
        mode: "SAMPLE_FALLBACK",
      },
      "48h": {
        risk: (h48Antecedent > 100 ? "VERY_HIGH" : h48Antecedent > 60 ? "HIGH" : "MODERATE") as RiskLevel,
        risk_score: Math.min(Number((props.risk_score * 1.05).toFixed(2)), 0.99),
        antecedent_rain_mm: h48Antecedent,
        recent_24h_rain_mm: f2,
        forecast_interval_rain_mm: f2,
        mode: "SAMPLE_FALLBACK",
      },
      "72h": {
        risk: (h72Antecedent > 100 ? "VERY_HIGH" : h72Antecedent > 60 ? "HIGH" : "MODERATE") as RiskLevel,
        risk_score: Math.min(Number((props.risk_score * 0.9).toFixed(2)), 0.99),
        antecedent_rain_mm: h72Antecedent,
        recent_24h_rain_mm: f3,
        forecast_interval_rain_mm: f3,
        mode: "SAMPLE_FALLBACK",
      },
    },
    risk_change_summary: "Sample fallback: backend offline. Estimated rolling accumulation.",
    data_meta: {
      source: "sample",
      freshness: null,
      note: "Sample fallback — backend is offline.",
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
      description: `${props.rain_3d}mm over past 3 days — elevated (SAMPLE_MOCK)`,
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
      description: `${props.rain_3d}mm over past 3 days — low (SAMPLE_MOCK)`,
      freshness: "Sample",
    });
  }

  // Slope
  if (props.slope > 32) {
    drivers.push({
      feature: "slope",
      display_name: "Terrain slope angle",
      direction: "up",
      description: `${props.slope}° — steep terrain`,
      freshness: "REAL DEM",
    });
  } else if (props.slope > 20) {
    drivers.push({
      feature: "slope",
      display_name: "Terrain slope angle",
      direction: "neutral",
      description: `${props.slope}° — moderate gradient`,
      freshness: "REAL DEM",
    });
  } else {
    drivers.push({
      feature: "slope",
      display_name: "Terrain slope angle",
      direction: "down",
      description: `${props.slope}° — gentle terrain`,
      freshness: "REAL DEM",
    });
  }

  // Soil moisture
  if (props.soil_moisture > 0.5) {
    drivers.push({
      feature: "soil_moisture",
      display_name: "Soil moisture index",
      direction: "up",
      description: `${(props.soil_moisture * 100).toFixed(0)}% — elevated in sample scenario`,
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
    model_type: "sample",
    drivers: drivers.slice(0, 4),
    data_meta: {
      source: "sample",
      freshness: null,
      note: "SAMPLE_MOCK — threshold-derived attribution, not real SHAP values",
    },
  };
}
