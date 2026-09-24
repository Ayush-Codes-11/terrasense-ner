import { useCallback, useEffect, useRef, useState } from "react";
import { fetchOperationalFacilities, fetchOperationalRoads, fetchOsmStatus } from "../services/spatial";
import type { OperationalFeatureCollection, OSMStatus } from "../services/spatial";

export type OperationalLoadState = "idle" | "loading" | "ready" | "error";
export interface OperationalLayerState {
  enabled: boolean;
  state: OperationalLoadState;
  data?: OperationalFeatureCollection;
  error?: string;
}
export interface OperationalLayersState {
  available: boolean;
  facilities: OperationalLayerState;
  roads: OperationalLayerState;
  osmStatus?: OSMStatus;
  toggleFacilities: () => void;
  toggleRoads: () => void;
  retryFacilities: () => void;
  retryRoads: () => void;
}

const initialLayer: OperationalLayerState = { enabled: false, state: "idle" };

export function useOperationalLayers(available: boolean): OperationalLayersState {
  const [facilities, setFacilities] = useState<OperationalLayerState>(initialLayer);
  const [roads, setRoads] = useState<OperationalLayerState>(initialLayer);
  const [osmStatus, setOsmStatus] = useState<OSMStatus>();
  const statusStarted = useRef(false);
  const facilityRequest = useRef<AbortController | undefined>(undefined);
  const roadRequest = useRef<AbortController | undefined>(undefined);
  const statusRequest = useRef<AbortController | undefined>(undefined);

  useEffect(() => {
    if (!available || !facilities.enabled || facilities.state !== "idle" || facilityRequest.current) return;
    const controller = new AbortController();
    facilityRequest.current = controller;
    setFacilities(current => ({ ...current, state: "loading", error: undefined }));
    void fetchOperationalFacilities(controller.signal)
      .then(data => { if (!controller.signal.aborted) setFacilities(current => ({ ...current, state: "ready", data, error: undefined })); })
      .catch(() => { if (!controller.signal.aborted) setFacilities(current => ({ ...current, state: "error", error: "Facility data is unavailable." })); })
      .finally(() => { if (facilityRequest.current === controller) facilityRequest.current = undefined; });
  }, [available, facilities.enabled, facilities.state]);

  useEffect(() => {
    if (!available || !roads.enabled || roads.state !== "idle" || roadRequest.current) return;
    const controller = new AbortController();
    roadRequest.current = controller;
    setRoads(current => ({ ...current, state: "loading", error: undefined }));
    void fetchOperationalRoads(controller.signal)
      .then(data => { if (!controller.signal.aborted) setRoads(current => ({ ...current, state: "ready", data, error: undefined })); })
      .catch(() => { if (!controller.signal.aborted) setRoads(current => ({ ...current, state: "error", error: "Road data is unavailable." })); })
      .finally(() => { if (roadRequest.current === controller) roadRequest.current = undefined; });
  }, [available, roads.enabled, roads.state]);

  useEffect(() => {
    if (!available || (!facilities.enabled && !roads.enabled) || statusStarted.current) return;
    const controller = new AbortController();
    statusRequest.current = controller;
    statusStarted.current = true;
    void fetchOsmStatus(controller.signal)
      .then(status => { if (!controller.signal.aborted) setOsmStatus(status); })
      .catch(() => undefined)
      .finally(() => { if (statusRequest.current === controller) statusRequest.current = undefined; });
  }, [available, facilities.enabled, roads.enabled]);

  useEffect(() => () => {
    facilityRequest.current?.abort();
    roadRequest.current?.abort();
    statusRequest.current?.abort();
  }, []);

  const toggleFacilities = useCallback(() => setFacilities(current => ({ ...current, enabled: !current.enabled })), []);
  const toggleRoads = useCallback(() => setRoads(current => ({ ...current, enabled: !current.enabled })), []);
  const retryFacilities = useCallback(() => setFacilities(current => ({ ...current, state: "idle", error: undefined })), []);
  const retryRoads = useCallback(() => setRoads(current => ({ ...current, state: "idle", error: undefined })), []);

  return { available, facilities, roads, osmStatus, toggleFacilities, toggleRoads, retryFacilities, retryRoads };
}
