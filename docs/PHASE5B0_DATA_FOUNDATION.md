# Phase 5B-0: Susceptibility data licensing and terrain foundation

## Status and scope

Phase 5B-0 establishes a reproducible, dry-run-first foundation for a future
Mizoram-wide static terrain susceptibility experiment. It does not download the
statewide DEM, prepare landslide labels or backgrounds, train a model, publish
SHAP explanations, add an API, or change the production application.

The governing Phase 5A decision remains **CONDITIONAL GO**. The planned study
unit remains a fixed 90 m grid in EPSG:32646, and any future labels remain
presence/background rather than positive/negative ground truth. The existing
relative prototype risk scorer remains unchanged and is not a probability.

## Copernicus licence record

The TerraSense project owner accepted the **Licence for Copernicus DEM instance
COP-DEM-GLO-30-F Global 30m Full, Free & Open** on **2026-09-26** for use in
TerraSense.

- Authoritative licence:
  <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf>
- Product: Copernicus DEM GLO-30 Public, `COP-DEM_GLO-30-DGED`
- Fixed source release for this foundation: 2021 AWS public release
- Distribution: AWS Registry of Open Data / Sinergise Cloud Optimized GeoTIFF
  conversion, anonymous public access:
  <https://registry.opendata.aws/copernicus-dem/>
- Product handbook: Copernicus DEM Product Handbook version 5.0, 2022-11-29
  <https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf>
- AWS COG conversion and grid-size notes:
  <https://copernicus-dem-30m.s3.amazonaws.com/readme.html>
- GDAL PixelIsPoint affine interpretation:
  <https://gdal.org/en/stable/development/rfc/rfc33_gtiff_pixelispoint.html>
- Horizontal reference: WGS 84, EPSG:4326
- Vertical reference: EGM2008, EPSG:3855, metres

The accepted rights include reproduction, distribution, communication to the
general public, adaptation, modification, and combination. The following
obligations apply:

1. Raw-data distribution must carry the required source notice:

   > © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.

2. Adapted or modified products must carry the required derivative notice:

   > produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved

3. Public communication or distribution must include this liability notice:

   > The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30

4. TerraSense must not imply endorsement by the provider, licensor, or
   Copernicus organisations.
5. If TerraSense grants downstream redistribution or public-communication
   rights, downstream users must remain bound by the applicable attribution,
   liability, and non-endorsement obligations.
6. Raw GLO-30 tiles may be redistributed under those conditions. The derived
   90 m predictor stack may be redistributed as an adapted product under the
   derivative notice and the same liability, non-endorsement, and downstream
   obligations.

This record is acceptance of the Copernicus licence only. It is not acceptance
or resolution of any Geological Survey of India terms.

## Unresolved GSI permissions

GSI BhooSanket permissions remain a blocking gate. The current repository
snapshot contains 2,046 occurrence records queried from the official
`Landslide_Public` FeatureServer layer at
<https://bhusanket.gsi.gov.in/gisserver/rest/services/Hosted/Public_Portal_Dashboard_Map/FeatureServer/0>,
but its saved metadata does not contain an express model-training or
redistribution licence. The official GSI portal terms at
<https://bhusanket.gsi.gov.in/terms.html> say reproduction requires prior
permission by email and acknowledgement of the source. Public query access
does not itself grant training,
transformation, redistribution, commercial/competition, derived-model, or
model-output publication rights.

The raw GSI coordinates currently present in the public repository and copied
into the backend deployment bundle are therefore a redistribution concern for
owner/legal review. Phase 5B-0 does not remove or alter them. Until written
permission resolves the permitted purposes and artifacts, TerraSense must not:

- reacquire or transform GSI records for training;
- create presence/background training data from them;
- train or publish a model derived from them;
- redistribute a new raw or prepared inventory snapshot;
- claim that derived models or outputs may be published.

### Alternative occurrence data remains conditional

No alternative inventory was downloaded or substituted. The main options for
a later, separately reviewed licensing checkpoint are:

- NASA Global Landslide Catalog/COOLR provides global coordinates and event
  dates, but the current NASA catalogue page labels its licence as unspecified
  and says export requires acceptance of separate terms. General NASA open-data
  policy does not establish rights for third-party records in a compiled
  inventory. Its English-language media and populated-area reporting bias also
  requires explicit treatment.
  <https://data.nasa.gov/dataset/global-landslide-catalog-export>
- NRSC/ISRO's Landslide Atlas reports approximately 80,000 Indian occurrences
  from 1998–2022. NRSC terms permit downloadable material for non-commercial
  use with attribution and allow derivative works, but raw redistribution and
  coordinate-level Mizoram access remain unverified.
  <https://www.nrsc.gov.in/nrscnew/resources_atlas_landslide.php>
- The Unified Global Landslide Catalogue publishes 1,061,450 point records
  under CC BY-NC 4.0 with heterogeneous spatial-accuracy classes. A Mizoram
  count and source-overlap audit would be required, and its non-commercial
  restriction is incompatible with an unrestricted operational release.
  <https://essd.copernicus.org/articles/18/4697/2026/>

Mixing any candidate with GSI would require source-aware duplicate resolution,
event-definition reconciliation, positional-quality filtering, and a new bias
analysis. Public availability alone is not a substitution decision.

## Dry-run tile plan

`scripts/acquire_mizoram_dem.py` reads the canonical current Mizoram ADM1
feature (`IN-MZ`) from `data/geodata/ner/states.geojson`, intersects that
geometry with one-degree cells, and sorts the resulting tile identifiers. It
then performs bounded anonymous HTTP HEAD requests. Default execution writes a
deterministic plan manifest and never makes a raster GET request.

The boundary currently requires eight source cells:

| Tile | Bounds (EPSG:4326) | Expected bytes |
| --- | --- | ---: |
| `Copernicus_DSM_COG_10_N21_00_E092_00_DEM` | 92–93 E, 21–22 N | 50,653,723 |
| `Copernicus_DSM_COG_10_N21_00_E093_00_DEM` | 93–94 E, 21–22 N | 46,417,416 |
| `Copernicus_DSM_COG_10_N22_00_E092_00_DEM` | 92–93 E, 22–23 N | 49,849,547 |
| `Copernicus_DSM_COG_10_N22_00_E093_00_DEM` | 93–94 E, 22–23 N | 45,171,500 |
| `Copernicus_DSM_COG_10_N23_00_E092_00_DEM` | 92–93 E, 23–24 N | 49,693,712 |
| `Copernicus_DSM_COG_10_N23_00_E093_00_DEM` | 93–94 E, 23–24 N | 44,870,628 |
| `Copernicus_DSM_COG_10_N24_00_E092_00_DEM` | 92–93 E, 24–25 N | 51,432,877 |
| `Copernicus_DSM_COG_10_N24_00_E093_00_DEM` | 93–94 E, 24–25 N | 45,757,139 |

Total expected remote size: **383,846,542 bytes (approximately 366.1 MiB)**.
The committed plan records each ETag as `provider_object_etag`; it does not call
the ETag a provider checksum. The provider publishes no SHA-256 values through
these metadata responses. `local_sha256` therefore remains `null` until a
future approved acquisition calculates it from the complete local file.

The completed Phase 5B-0 dry run downloaded **zero raster bytes**. No
`local-data/susceptibility` directory was created by it.

## Environment

Use a worktree-local, ignored Python 3.13 environment. Installation is limited
to the dependencies already declared in `backend/requirements-dev.txt`.

Windows PowerShell:

```powershell
py -3.13 -m venv .venv-phase5b0
.\.venv-phase5b0\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv-phase5b0\Scripts\python.exe scripts\acquire_mizoram_dem.py
```

POSIX shell with Python 3.13 available:

```sh
python3.13 -m venv .venv-phase5b0
./.venv-phase5b0/bin/python -m pip install -r backend/requirements-dev.txt
./.venv-phase5b0/bin/python scripts/acquire_mizoram_dem.py
```

The verified Windows environment used Python 3.13.15, NumPy 2.5.3, Rasterio
1.5.1, GDAL 3.12.4, PyProj 3.8.0, PROJ 9.8.1, Shapely 2.1.2, and GEOS 3.13.1.
GeoPandas is not declared, was not installed, and is not required by either
utility.

## Acquisition safety and future command

The acquisition utility:

- defaults to plan-only mode;
- requires both `--download` and `--confirm-download` for any raster GET;
- refuses download unless licence acceptance is present in the plan;
- permits only HTTPS requests to the exact public
  `copernicus-dem-30m.s3.amazonaws.com` tile path and rejects redirects;
- validates tile identifiers before constructing or inspecting local paths;
- downloads only missing files and writes through `.part` files;
- supports HTTP range resume when the server returns `206`;
- validates the complete `Content-Range`, and safely restarts when a server
  ignores a range request and returns `200`;
- uses three bounded attempts and a 20-second per-request timeout by default;
- requires enough free space for the complete plan plus the recorded 2 GiB
  reserve before creating the raw-data directory;
- rejects HTML, XML, JSON, and non-TIFF signatures;
- validates raster readability, one-band float32 content, EPSG:4326, dimensions,
  and the exact `RasterPixelIsPoint` grid declared by `AREA_OR_POINT=Point`;
- keeps the one-degree plan bounds as nominal tile-selection bounds while deriving
  GDAL's area-oriented affine footprint by shifting the point-posted northwest
  sample half a pixel west and north; the AWS COG conversion removes the shared
  east and south posts, so a 3600 x 3600 one-degree tile at nominal bounds
  `(W, S, E, N)` has resolution `d = 1/3600` degree and affine bounds
  `(W - d/2, S + d/2, E - d/2, N + d/2)`; arbitrary bounds tolerances,
  missing/contradictory grid semantics, rotation, shear, or translated grids
  are rejected;
- refuses to overwrite an existing file whose size differs or whose SHA-256
  differs from an existing acquisition manifest;
- calculates local SHA-256 after full validation and records UTC retrieval time;
- contains no credentials, cookies, signed URLs, or machine-specific paths.

The following command is documented for review but **is not authorized in
Phase 5B-0**:

```powershell
.\.venv-phase5b0\Scripts\python.exe scripts\acquire_mizoram_dem.py --download --confirm-download
```

A separate owner approval for the exact 383,846,542-byte plan is required
before anyone runs it.

## Storage and repository boundary

```text
local-data/susceptibility/                    # ignored; training workstation only
  copernicus-glo30-2021/
    raw/                                      # immutable downloaded COGs
    acquisition_manifest.json                # local retrieval/SHA-256 record
    work/                                     # temporary mosaics or VRTs
    derived/terrain-v1/
      mizoram_terrain_predictors_v1.tif
      manifest.json

docs/manifests/susceptibility/                # small reviewed plans only
artifacts/ml/susceptibility/                  # ignored future model/evaluation files
```

The ignored `local-data/susceptibility` tree is outside the canonical `data/`
tree consumed by `sync_deployment_bundle.py`. Raw tiles, temporary mosaics,
VRTs, derived rasters, training tables, models, and evaluation artifacts cannot
enter the backend/Vercel bundle through canonical data synchronization. The
reviewed plan manifest is documentation-owned for the same reason. A 2 GiB
free-space reserve is required before acquisition.

Expected working sizes are approximately 366.1 MiB compressed raw data,
395.5 MiB of uncompressed source pixels, and 97.7 MiB for six statewide
float32 bands before compression. Windowing and temporary files can increase
peak use; retain at least the 2–8 GiB RAM allowance established by Phase 5A.

## Deterministic target grid and predictors

`scripts/build_mizoram_terrain_predictors.py` consumes only validated GLO-30
COGs from the ignored raw directory. It cannot use the existing Aizawl
Terrarium visualization assets.

- Target CRS: EPSG:32646, WGS 84 / UTM zone 46N
- Resolution: exactly 90 m
- Origin: extent snapped outward to exact 90 m multiples from the EPSG:32646
  origin
- Processing buffer: 270 m on all sides before snapping
- Current grid: 1,342 columns × 3,180 rows
- Final mask: current canonical Mizoram geometry, pixel-centre inclusion,
  `all_touched=false`
- Vertical datum: source EGM2008 heights retained without vertical
  transformation
- Data type: float32
- Nodata: `-9999.0`
- Output: six-band GeoTIFF, DEFLATE level 9, floating-point predictor,
  deterministic band ordering and metadata

Elevation is resampled first to the fixed 90 m metric grid using GDAL average
resampling, which area-aggregates contributing continuous source elevation
pixels. All terrain derivatives are then calculated on that final buffered
grid. The state mask is applied only after derivatives are complete.

1. `elevation_m`: the 90 m average-resampled elevation.
2. `slope_deg`: Horn 3×3 gradient magnitude converted to degrees.
3. `aspect_sin` and `aspect_cos`: sine and cosine of the Horn downslope
   direction, clockwise from grid north. Flat cells use `(0, 0)`.
4. `curvature_laplacian_per_m`:

   ```text
   (zE - 2*zC + zW) / 90² + (zN - 2*zC + zS) / 90²
   ```

5. `tpi_3x3_m`: centre elevation minus the arithmetic mean of all eight
   adjacent 90 m cells.

Every derivative requires a complete valid 3×3 neighborhood. Source nodata,
any invalid neighbor, and the outer raster edge propagate to derivative nodata.
The output excludes rainfall, soil moisture, forecasts, roads, settlements,
facilities, exposure/access, GSI attributes, and prototype risk values.

Raw-to-derived lineage is:

```text
canonical Mizoram ADM1 + eight validated GLO-30 COGs
  -> deterministic EPSG:32646 buffered 90 m elevation grid
  -> six terrain bands calculated before masking
  -> current Mizoram boundary mask
  -> checksummed ignored predictor GeoTIFF + local derivation manifest
```

The future build command, after separately approved acquisition, is:

```powershell
.\.venv-phase5b0\Scripts\python.exe scripts\build_mizoram_terrain_predictors.py
```

## Checksums, tests, and reproducibility limits

The planned manifest is deterministic and stores the canonical boundary
SHA-256, URLs, bounds, remote sizes, ETags, licence record, and `null` local
checksums. A future acquisition manifest will store computed local SHA-256
values; ETags remain separately labelled. The derived manifest will record all
source SHA-256 values, the snapped transform, dimensions, definitions,
software versions, and the final predictor-stack SHA-256.

The offline synthetic suite creates temporary GeoTIFFs during testing. It
covers tile selection and ordering, plan-only behavior, metadata changes,
timeouts, corrupt content, existing-file checks, overwrite refusal, grid
alignment, CRS, nodata, analytic planar slopes and aspects, the flat-aspect
rule, curvature, TPI, processing buffer, boundary masking, deterministic output,
compression, metadata, and data types. Standard tests do not require network
access. The live dry run is a separate metadata-only operational check.

Reproducibility remains bounded by the fixed 2021 AWS release, the committed
boundary version, GDAL/PROJ numerical behavior, and future availability of the
public objects. A model still cannot be trained or published until the GSI
rights gate and every Phase 5A validation gate are resolved.

## Next approval boundary

Phase 5B-0 stops with source code, documentation, a plan manifest, and synthetic
tests. The next possible action is the eight-tile acquisition. It requires a
separate explicit owner authorization for **383,846,542 bytes**, after review of
the final diff and dry-run output. That approval would permit source download
and checksum validation only; it would not permit GSI preparation, background
sampling, model training, SHAP, API/frontend work, publication, or deployment.
