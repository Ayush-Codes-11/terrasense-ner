# Phase 4B: Aizawl 3D terrain

Phase 4B adds an opt-in, genuine terrain view for the Aizawl detailed pilot. The approved Leaflet map remains the default 2D renderer. MapLibre GL JS and the elevation tiles are loaded only after the user selects **3D** in the existing Map View menu.

## Data and scope

The terrain source is the local validated `copernicus_glo30_aizawl.tif` crop prepared by `backend/scripts/fetch_or_prepare_dem.py`.

- Product: Copernicus DEM GLO-30 DSM
- Resolution: approximately 30 m / 1 arc-second
- Coverage: the Aizawl detailed-pilot envelope only
- Terrain scale: 1.0; no vertical exaggeration
- Web encoding: 256 × 256 Terrarium PNG tiles, Web Mercator XYZ, zooms 8–13
- Runtime path: `/terrain/aizawl/v1/`

This is a static elevation model. It is not live terrain, a building-level surface, a landslide probability, or a new risk input. Risk values and provenance continue to come from the existing APIs.

Attribution: © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. Distributed via AWS Open Data/Sinergise.

## Reproduce and validate the tiles

The raw GeoTIFF is deliberately ignored and is never copied into the frontend bundle. From the repository root, install the pinned tooling in an isolated environment and run:

```powershell
python -m pip install -r scripts/requirements-terrain.txt
python scripts/prepare_aizawl_terrain_tiles.py --check --verify-determinism
```

Generation refuses to replace an existing version directory. Publish a new versioned directory for a changed source or algorithm. `--check` rebuilds into temporary directories and compares every committed file checksum without modifying the output.

The manifest records the source checksum, CRS, bounds, resolution, nodata contract, encoding formula, zoom coverage, output checksums, compressed size, measured encoding error, and cross-tile boundary continuity. Source rasters with nodata inside the declared rectangular coverage fail generation. Pixels in the unused portion of boundary XYZ tiles are edge-clamped and hidden by the TileJSON bounds.

## Runtime behavior

- 2D is always the initial mode.
- Street, Terrain and Satellite are cartographic basemaps and remain independent from the 2D/3D display choice.
- 3D is offered only for the Aizawl detailed pilot and only when WebGL2 is available.
- Switching renderers preserves the URL hierarchy selection and selected zone.
- WebGL initialization, context-loss, or terrain-tile failure returns explicitly to 2D with a sanitized message.
- A basemap failure does not substitute a different provider; terrain and hierarchy overlays remain available with a notice.
- MapLibre is removed when leaving 3D, releasing its canvas, workers and WebGL resources.

OpenStreetMap, OpenTopoMap and Esri attribution remains provider-specific in both renderers. “Terrain” in the basemap section means the OpenTopoMap cartographic style. “3D” means the Copernicus elevation display mode.

The hierarchy source remains file-backed by default. PostGIS remains opt-in and uses the same additive GeoJSON contract; production PostGIS cutover is still deferred.

## Deployment and caching

The versioned terrain pyramid is static and may be cached immutably. `tiles.json` and `manifest.json` identify the version and coverage. Dynamic hierarchy, weather and risk responses must retain their existing refresh and cache behavior and must not inherit an indefinite terrain-asset cache policy.

If the pilot assets later move to object storage, use immutable paths, read-only public access, correct PNG/JSON MIME types, explicit browser CORS for approved frontend origins, and the same attribution. Do not proxy arbitrary terrain URLs through FastAPI.
