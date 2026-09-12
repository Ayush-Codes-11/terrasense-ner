import type { Boundaries, ZoneList } from "../services/spatial";
export const AIZAWL = "IND-ADM2-76128533B34203923268864";
export interface Selection { state?: string; district?: string; zone?: string }
export function readSelection(params: URLSearchParams): Selection {
  return { state: params.get("state") || undefined, district: params.get("district") || undefined, zone: params.get("zone") || undefined };
}
export function selectLevel(selection: Selection, level: "region" | "state" | "district" | "zone", id?: string): Selection {
  if (level === "region") return {};
  if (level === "state") return { state: id };
  if (level === "district") return { state: selection.state, district: id };
  return { ...selection, zone: id };
}
export const riskColors: Record<string, string> = { LOW: "#36a875", MODERATE: "#e3c34b", HIGH: "#ef8a36", VERY_HIGH: "#df4b53" };
export function riskLabel(band?: string) { return band && band in riskColors ? band.replaceAll("_", " ") : "Risk unavailable"; }
export function pilotZones(grid: Boundaries, metadata: ZoneList, district: string): Boundaries {
  const bound = new Map(metadata.items.map(z => [z.zone_id, z]));
  if (district !== AIZAWL || !metadata.detailed_zone_model_available) return { type: "FeatureCollection", features: [] };
  const features = grid.features.filter(f => bound.has(f.properties.zone_id ?? "")).map(f => ({ ...f, properties: bound.get(f.properties.zone_id!)! }));
  if (features.length !== metadata.count || new Set(features.map(f => f.properties.zone_id)).size !== metadata.count || features.some(f => f.properties.district_id !== district)) throw new Error("Zone binding mismatch");
  return { type: "FeatureCollection", features };
}
