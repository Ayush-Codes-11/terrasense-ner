export const PROVENANCE_LABELS: Record<string, string> = {
  "REAL_DEM": "Copernicus DEM GLO-30 (real satellite data)",
  "REAL_GPM": "NASA GPM IMERG (real satellite rainfall)",
  "REAL_FORECAST": "ECMWF IFS HRES via Open-Meteo (real forecast)",
  "REAL_SOIL_MOISTURE": "NASA SMAP L4 (real satellite soil moisture)",
  "SAMPLE_MOCK": "Sample/placeholder data (not live)",
  "SAMPLE_GPM_COMPATIBLE": "GPM-schema-compatible offline fixture (not live)"
};

export function formatProvenanceLabel(code: string): string {
  return PROVENANCE_LABELS[code] || code;
}