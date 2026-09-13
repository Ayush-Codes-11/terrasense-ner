import { lazy, Suspense } from "react";
import HierarchyMap from "./HierarchyMap";
import type { HierarchyMapProps } from "./HierarchyMap";
import type { DisplayMode } from "./mapConfig";

const TerrainMap3D = lazy(() => import("./TerrainMap3D"));

interface Props extends HierarchyMapProps {
  displayMode: DisplayMode;
  onModeFailure: (message: string) => void;
}

export default function MapSurface({ displayMode, onModeFailure, ...mapProps }: Props) {
  if (displayMode === "2d") return <HierarchyMap {...mapProps} />;
  return <Suspense fallback={<div className="gis-map-empty" role="status">Loading approximately 30 m Copernicus terrain…</div>}>
    <TerrainMap3D {...mapProps} onFailure={onModeFailure} />
  </Suspense>;
}
