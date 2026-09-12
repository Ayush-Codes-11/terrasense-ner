import { useEffect, useState } from "react";
import { spatialFetch } from "../services/spatial";
import type { RiskRecord, WeatherContext } from "../services/spatial";
export function usePilotRisk(enabled: boolean, zone?: string) {
  const [risks, setRisks] = useState<RiskRecord[]>([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [retrieved, setRetrieved] = useState<string>();
  const [weather, setWeather] = useState<{ zone: string; value: WeatherContext }>();
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const refresh = async () => {
      setLoading(true);
      try {
        const response = await spatialFetch<{ zones: RiskRecord[] }>("/risk/current", 0);
        if (active) { setRisks(response.zones); setError(false); setRetrieved(new Date().toISOString()); }
      } catch { if (active) { setRisks([]); setError(true); } }
      finally { if (active) setLoading(false); }
    };
    void refresh();
    const timer = setInterval(refresh, 60_000);
    return () => { active = false; clearInterval(timer); };
  }, [enabled]);
  useEffect(() => {
    if (!enabled || !zone) return;
    let active = true;
    const refresh = () => spatialFetch<WeatherContext>(`/weather/${encodeURIComponent(zone)}`, 0)
      .then(value => { if (active) setWeather({ zone, value }); })
      .catch(() => { if (active) setWeather(undefined); });
    void refresh();
    const timer = setInterval(refresh, 60_000);
    return () => { active = false; clearInterval(timer); };
  }, [enabled, zone]);
  return { risks: enabled ? risks : [], error, loading, retrieved, weather: weather && weather.zone === zone ? weather.value : undefined };
}
