import { useEffect, useState } from "react";
import { spatialFetch, SpatialError } from "../services/spatial";
import type { Boundaries, DistrictInfo, StateInfo, ZoneList } from "../services/spatial";
import { AIZAWL, pilotZones } from "../utils/navigation";
import type { Selection } from "../utils/navigation";
export interface HierarchyView { states: Boundaries; districts?: Boundaries; zones?: Boundaries; state?: StateInfo; district?: DistrictInfo; detailed?: boolean }
export function useHierarchyMap(selection: Selection, retry: number): { loading: boolean; data?: HierarchyView; error?: string } {
  const [result, setResult] = useState<{ key: string; data?: HierarchyView; error?: string }>({ key: "" });
  const key = JSON.stringify([selection.state, selection.district, selection.zone, retry]);
  useEffect(() => {
    let active = true;
    (async () => {
      const states = await spatialFetch<Boundaries>("/regions/NER/states?include_geometry=true");
      const data: HierarchyView = { states };
      if (!selection.state && (selection.district || selection.zone)) throw new SpatialError(404);
      if (selection.state) {
        data.state = states.features.find(f => f.properties.state_id === selection.state)?.properties as StateInfo | undefined;
        if (!data.state) throw new SpatialError(404);
        data.districts = await spatialFetch<Boundaries>(`/states/${encodeURIComponent(selection.state)}/districts?include_geometry=true`);
      }
      if (selection.district) {
        data.district = data.districts?.features.find(f => f.properties.district_id === selection.district)?.properties as DistrictInfo | undefined;
        if (!data.district) throw new SpatialError(404);
        const metadata = await spatialFetch<ZoneList>(`/districts/${encodeURIComponent(selection.district)}/zones`);
        data.detailed = data.district.district_id === AIZAWL && data.district.coverage_level === "DETAILED_PILOT" && metadata.detailed_zone_model_available;
        if (data.detailed) data.zones = pilotZones(await spatialFetch<Boundaries>("/zones"), metadata, selection.district);
      }
      if (selection.zone && !data.zones?.features.some(f => f.properties.zone_id === selection.zone)) throw new SpatialError(404);
      if (active) setResult({ key, data });
    })().catch(error => { if (active) setResult({ key, error: error instanceof SpatialError ? error.message : "Spatial data is temporarily unavailable." }); });
    return () => { active = false; };
  }, [key, selection.state, selection.district, selection.zone]);
  return result.key === key ? { ...result, loading: false } : { loading: true };
}
