// ============================================================
// useAllZoneRisks — fetches current risk for all 25 zones from FastAPI
// GET /risk/current (computed dynamically by ml.prototype_scorer).
//
// Falls back to local GeoJSON precomputed values if backend is offline.
// ============================================================

import { useState, useEffect, useMemo } from "react";
import type { Zone } from "../types";
import { getAllZoneRisks } from "../services/api";

export interface AllZoneRisksResult {
  zoneRisksMap: Map<string, Zone>;
  zonesList: Zone[];
  loading: boolean;
  apiOnline: boolean | null;
  isFallback: boolean;
  error: string | null;
}

export function useAllZoneRisks(fallbackZones: Zone[]): AllZoneRisksResult {
  const [apiZones, setApiZones] = useState<Zone[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getAllZoneRisks()
      .then((zones) => {
        if (!cancelled) {
          setApiZones(zones);
          setApiOnline(true);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setApiZones(null);
          setApiOnline(false);
          setError(String(err));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const isFallback = !apiZones || apiZones.length === 0;

  const zonesList = useMemo(() => {
    return apiZones && apiZones.length > 0 ? apiZones : fallbackZones;
  }, [apiZones, fallbackZones]);

  const zoneRisksMap = useMemo(() => {
    const map = new Map<string, Zone>();
    zonesList.forEach((z) => map.set(z.zone_id, z));
    return map;
  }, [zonesList]);

  return {
    zoneRisksMap,
    zonesList,
    loading,
    apiOnline,
    isFallback,
    error,
  };
}
