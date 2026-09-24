import type { OperationalFeatureCollection, OperationalFeatureProperties } from "../services/spatial";

const CATEGORY_COLORS: Record<string, string> = {
  hospital: "#e85d75",
  clinic: "#f59e0b",
  police: "#38bdf8",
  primary_health_centre: "#f59e0b",
  emergency_centre: "#14b8a6",
};

export function facilityCategory(properties?: OperationalFeatureProperties | null): string {
  const value = properties?.category ?? properties?.facility_type ?? properties?.amenity ?? properties?.healthcare ?? "facility";
  return String(value).trim().toLowerCase().replace(/\s+/g, "_") || "facility";
}

export function facilityCategoryLabel(category: string): string {
  return category.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
}

export function facilityColor(category: string): string {
  return CATEGORY_COLORS[category] ?? "#14b8a6";
}

export function facilityCategories(data?: OperationalFeatureCollection): string[] {
  return data ? [...new Set(data.features.map(feature => facilityCategory(feature.properties)))].sort() : [];
}

export function operationalProvenance(data?: OperationalFeatureCollection): string {
  if (!data) return "Unavailable";
  return data.data_meta.data_type === "REAL_OSM" ? "Cached OSM snapshot" : "Sample fallback · fictitious test data";
}
