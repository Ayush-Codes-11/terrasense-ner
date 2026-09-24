import { useCallback, useEffect, useRef, useState } from "react";
import { fetchZoneExposure } from "../services/spatial";
import type { ZoneExposure } from "../services/spatial";

interface ZoneExposureState {
  data?: ZoneExposure;
  loading: boolean;
  error?: string;
  retry: () => void;
}

export function useZoneExposure(zoneId: string): ZoneExposureState {
  const [state, setState] = useState<{ zoneId?: string; data?: ZoneExposure; error?: string }>({});
  const [attempt, setAttempt] = useState(0);
  const requestId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const currentRequest = ++requestId.current;
    if (!zoneId) {
      return () => controller.abort();
    }

    void fetchZoneExposure(zoneId, controller.signal)
      .then(response => {
        if (!controller.signal.aborted && currentRequest === requestId.current && response.zone_id === zoneId) setState({ zoneId, data: response });
      })
      .catch(() => {
        if (!controller.signal.aborted && currentRequest === requestId.current) setState({ zoneId, error: "Exposure calculations are temporarily unavailable." });
      });

    return () => controller.abort();
  }, [zoneId, attempt]);

  const retry = useCallback(() => {
    setState({});
    setAttempt(value => value + 1);
  }, []);
  const current = state.zoneId === zoneId;
  return { data: current ? state.data : undefined, loading: Boolean(zoneId) && !current, error: current ? state.error : undefined, retry };
}
