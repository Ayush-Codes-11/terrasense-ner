# Phase 5A — Static Landslide Susceptibility ML Readiness Audit

**Audit basis:** production `main` at `777c61b30c4c81a459f381fde6f4cba392f62a3c`

**Decision:** **CONDITIONAL GO** for a first, explicitly experimental, static susceptibility study.

**Recommended scope:** Mizoram-wide, presence-background modeling on a 90 m analysis grid in EPSG:32646.
**Not approved by this audit:** model training, production inference, replacement of the prototype risk endpoint, probability claims, dynamic rainfall-trigger modeling, or a frontend susceptibility layer.

## Executive conclusion

The repository contains a substantial real occurrence inventory: 2,046 geolocated GSI BhooSanket records for Mizoram. After exact-coordinate consolidation, 1,881 unique locations remain; at a 30 m grid, they occupy 1,865 cells. This is enough label volume to justify a carefully controlled static, presence-background experiment. It is not enough by itself to train an honest model.

Three gates prevent an immediate `GO`:

1. The repository does not contain a Mizoram-wide, analysis-ready predictor stack. Its real Copernicus GLO-30 terrain source covers only the Aizawl area, and the original GeoTIFF is absent from the checkout. No wall-to-wall geology, lithology, land-cover, vegetation, soil, drainage, or climatology layer is present.
2. The GSI files contain no license or terms permitting redistribution and model-training use. Public query access is evidence of accessibility, not evidence of a training or redistribution license.
3. The occurrence inventory is presence-only, spatially clustered, partly duplicated, and has mixed coordinate precision. It has no usable event dates and no recorded positional-accuracy or mapping-scale statement. A defensible pipeline must address inventory bias, false precision, spatial autocorrelation, and background sampling before model fitting.

The minimum truthful first experiment is therefore a **terrain-only relative susceptibility ranking** using newly prepared Mizoram-wide DEM derivatives: elevation, slope, sine and cosine of aspect, general curvature, and a fixed 3×3 terrain-position index (`tpi_3x3_m`). It may compare logistic regression, a tree-based baseline, and XGBoost. It must use spatial validation and must remain labelled `EXPERIMENTAL`. Its output would describe relative spatial predisposition under the study's sampling assumptions. It would not be a landslide probability, a forecast, a warning, an event-timing estimate, or evidence that any road or facility is safe.

The preferred geography is all of Mizoram. The current Aizawl district boundary contains only 303 inventory points, and the current 25-zone pilot contains 60 points in 59 occupied 30 m cells. The 25 zones must never be treated as 25 training rows. Aizawl can be a secondary geographic holdout or reporting subset after a statewide predictor stack exists.

## Repository and runtime baseline

The audit began from a clean sibling worktree on `phase5/ml-susceptibility-readiness`, created from `origin/main` at `777c61b30c4c81a459f381fde6f4cba392f62a3c`. Phase 4C feature commit `4adc0e1df390792304e653581511cbd2d504df1a` is an ancestor of that commit.

Production hierarchy behavior remains file-backed by default. `backend/services/hierarchy_source.py` uses `HIERARCHY_DATA_SOURCE=file` unless PostGIS is explicitly selected. The canonical `data/` and `ml/` trees are copied into `backend/data/` and `backend/ml/` by `backend/scripts/sync_deployment_bundle.py`, which excludes raw GeoTIFFs and verifies SHA-256 parity. A future susceptibility pipeline must respect this canonical/deployment split and must not silently put large training assets into the serverless bundle.

## Current scorer audit

The active model is a deterministic, heuristic relative prototype risk scorer, not trained ML. Its canonical implementation is in `ml/scorer_config.py`; a synchronized deployment copy exists under `backend/ml/`. `backend/services/risk_engine.py` selects it when `RISK_MODEL` is unset or equals `prototype`, which is the default. Any other configured model currently raises `NotImplementedError`.

The score is:

```text
prototype score =
    0.25 × min(max(mean_slope_deg / 40, 0), 1)
  + 0.30 × min(max(rainfall_24h_mm / 70, 0), 1)
  + 0.30 × min(max(rainfall_3d_mm / 150, 0), 1)
  + 0.15 × min(max(soil_wetness_index / 1, 0), 1)
```

Elevation and seven-day rainfall are returned as contextual features but do not contribute to this score. Categories use these inclusive lower bounds: `LOW` 0.00, `MODERATE` 0.25, `HIGH` 0.50, and `VERY_HIGH` 0.75.

For C03, the production route supplies mean slope 22.01°, GPM 24-hour rainfall 51.85 mm, GPM three-day rainfall 105.69 mm, and SMAP wetness 0.927588…. Their normalized values are 0.5503, 0.7407, 0.7046, and 0.9276. Weighted contributions are approximately 0.1376, 0.2222, 0.2114, and 0.1391, producing 0.7103 and category `HIGH`. Elevation is 980.8 m but is not scored. Existing tests lock this behavior.

The scorer metadata is explicit: `score_type=prototype_relative_risk_score`, `is_probability=false`, `is_calibrated=false`, and `computed_by=prototype_scorer_v1`. The frontend describes it as a relative prototype score and identifies static ML validation as pending. The Aizawl district model status is `STATIC_ML_VALIDATION_PENDING`; other districts are `NOT_IMPLEMENTED`.

The current 0.7103 result therefore remains a heuristic relative prototype risk score. It is not a trained probability or calibrated confidence value.

Input provenance is mixed:

| Input | Runtime provenance | Role |
| --- | --- | --- |
| Mean slope and elevation | `REAL_DEM`, derived from cached Copernicus DEM statistics | Terrain and context |
| 24-hour and three-day observed rainfall | `REAL_GPM`, cached three-day snapshot | Dynamic score inputs |
| Forecast rainfall | `REAL_FORECAST`, cached ECMWF/Open-Meteo response | Context only |
| Soil wetness used by the scorer | `REAL_SOIL_MOISTURE`, cached SMAP snapshot | Dynamic score input |
| Zone grid fallback properties | `SAMPLE_MOCK` | Prototype fallback/context; not training data |

Two existing provenance inconsistencies should be corrected before any experimental model is exposed, without changing the current score in this phase. The current-risk response retains legacy zone fields that show sample soil moisture `0.62`, while the scorer's feature payload correctly uses real SMAP wetness `0.9276`. Its top-level `data_meta` also describes rainfall and soil as sample data although `feature_provenance` correctly identifies the real cached inputs. In addition, the FastAPI root description says no real sensor data are active even though cached GPM, SMAP, and DEM inputs are active. These are contract/documentation issues, not evidence of trained ML.

No active code claims that 0.7103 is a probability, calibrated confidence, or trained prediction. The frontend contains dormant rendering branches for a future `xgboost`/SHAP response, but no route selects them and no trained model artifact exists.

### Declared ML/geospatial dependencies

| Library | Declared status |
| --- | --- |
| NumPy | Declared in backend runtime and `ml/requirements.txt` |
| PyProj | Declared in backend runtime |
| Rasterio | Declared in backend development requirements and used by terrain preparation |
| Shapely | Declared in backend runtime |
| Pillow | Declared for terrain tile preparation |
| XGBoost | Not declared |
| scikit-learn | Not declared |
| SHAP | Not declared |
| Pandas | Not declared |
| GeoPandas | Not declared |

No abandoned training script or serialized model (`pkl`, `joblib`, XGBoost binary/JSON/UBJ, ONNX, or equivalent) was found. Existing ignored model/raster patterns are policy placeholders, not evidence of artifacts. Sample-data documentation explicitly forbids using its fabricated values for ML.

## Historical landslide-label audit

### Source, identity, and geometry

`data/real/landslides/gsi_mizoram_complete.json` and `gsi_mizoram_raw.json` are byte-identical snapshots with SHA-256 `fcc5b94a098b856e61f516ae8df94fab042caa6908ccf84027e1b8222d7b21c6`. They were retrieved from the public GSI BhooSanket `Landslide_Public` ArcGIS FeatureServer layer using the filter `state='Mizoram'` and offset pagination. The service declares point geometry in EPSG:4326. All analysis in this audit treats longitude/latitude as WGS 84 because that CRS is declared by the service. The saved snapshot does not contain a reliable retrieval timestamp; recording one is a mandatory Phase 5B start gate.

| Measure | Result |
| --- | ---: |
| Total records | 2,046 |
| Records with valid in-range coordinates | 2,046 |
| Invalid or out-of-range coordinates | 0 |
| Exact unique coordinate locations | 1,881 |
| Exact duplicate coordinate groups | 108 |
| Records beyond the first in exact groups | 165 |
| Records participating in exact groups | 273 |
| Largest exact group | 9 records |
| Non-exact coordinate pairs within 30 m | 46 pairs / 82 records |
| Non-exact coordinate pairs within 100 m | 199 pairs / 288 records |
| Spatial bounds | 91.604533–93.394447° E; 22.050000–24.510000° N |
| Inside current Mizoram state geometry | 2,041 |
| Outside current Mizoram state geometry | 5 |
| Unassigned to a current district polygon | 30 |
| Inside current Aizawl district polygon | 303 |
| Inside the actual 25-zone polygon union | 60 |

The repository's earlier report lists 108 as “duplicate coordinate pairs”; direct analysis shows that 108 is the number of duplicated coordinate groups, while all pairwise combinations within those groups total 278. The operational deduplication quantity is 165 redundant records beyond one record per exact location.

### Count semantics and reproducible spatial method

These counts measure different stages and must not be substituted for one another. The 2,046 source-record count is the number of retrieved features. The 2,046 valid-coordinate count is the subset passing numeric and range validation; it happens to equal the source count. The 1,881 count is the number of distinct parsed coordinate pairs before projection. The 1,865 and 1,804 counts are occupied cells for all 2,046 valid source coordinates before clipping to the current state boundary. The 2,041 count is a boundary-membership count. The Aizawl and pilot counts are membership counts against different polygon sets. The 59 pilot-cell count is a cell-occupancy count for the 60 pilot-member records.

The audit calculation was performed as follows:

1. For each retrieved feature, parse ArcGIS geometry `x` and `y`; use attribute longitude and latitude only as a fallback. Accept only finite numeric longitude in `[-180, 180]` and latitude in `[-90, 90]`. Geometry and attribute coordinates agreed to approximately `1e-9` degrees at worst.
2. Define an exact duplicate by equality of the parsed IEEE-754 longitude/latitude tuple, with no rounding or tolerance. Count one unique location per tuple. Near-duplicate counts are separate Euclidean-distance audits after projection and exclude exact pairs.
3. Use `data/geodata/ner/states.geojson` and `districts.geojson`, both release `9469f09`. The state geometry is geoBoundaries gbOpen India ADM1, boundary vintage 2011; districts are ADM2, boundary vintage 2021. Both repository layers declare EPSG:4326.
4. Use the boundary-inclusive `covers(point)` predicate for state, district, Aizawl, pilot-union, and individual-zone membership. A point exactly on a polygon boundary therefore counts as inside. A boundary point could match more than one adjacent district or zone; the audit checked for this and found no multi-district and no multi-zone matches. Thirty records matched no current district polygon.
5. Define “inside Aizawl” as covered by the current ADM2 feature with district ID `IND-ADM2-76128533B34203923268864`, not by the source-reported district string. This produces 303 records; the source field's older Aizawl grouping contains 457.
6. Define “inside the 25-zone pilot grid” as covered by the geometric union of all 25 polygons in `data/sample/grid-risk.geojson`. That grid is explicitly `SAMPLE_MOCK`, approximate, and EPSG:4326. It is used here only to count spatial overlap with the existing UI pilot, never as model-training truth.
7. Transform every valid point from EPSG:4326 to EPSG:32646 with longitude passed as the x-axis. For resolution `r`, assign cell index `(floor(easting / r), floor(northing / r))`; the origin is therefore the EPSG:32646 false-origin coordinate system, not a fitted local origin. Count distinct indices at `r=30` and `r=90` metres. These are audit indices, not a claim that source accuracy equals either resolution.
8. The five records not covered by the current Mizoram state polygon remain in the all-source coordinate and occupancy audits, which is why the 1,865 and 1,804 figures are explicitly pre-clip counts. They must be excluded from the Phase 5B in-state training candidate set while remaining documented in the source manifest.

Coordinate precision is inconsistent. Latitude decimal-place counts are 46 at one decimal, 388 at two, 64 at three, 27 at four, 143 at five, 1,374 at six, and 4 at eight. Longitude counts are 3 at zero decimals, 22 at one, 401 at two, 18 at three, 16 at four, 144 at five, 1,438 at six, and 4 at eight. Values rounded to 0.01° imply roughly kilometre-scale precision, while six decimals imply sub-metre numeric precision that is not independently substantiated. The files provide no positional-accuracy or mapping-scale metadata. Numeric precision must therefore not be treated as measured accuracy.

### District assignment

The source-reported district field uses eight older district groupings:

| Reported district | Records |
| --- | ---: |
| Aizawl | 457 |
| Champhai | 447 |
| Kolasib | 94 |
| Lawngtlai | 226 |
| Lunglei | 431 |
| Mamit | 136 |
| Saiha | 106 |
| Serchhip | 149 |

A fresh point-in-polygon assignment against the repository's 2021 district geometry produces the following current geography:

| Current district | Records |
| --- | ---: |
| Aizawl | 303 |
| Champhai | 157 |
| Hnahthial | 75 |
| Khawzawl | 184 |
| Kolasib | 170 |
| Lawngtlai | 221 |
| Lunglei | 362 |
| Mamit | 124 |
| Saiha | 104 |
| Saitual | 164 |
| Serchhip | 152 |

The difference is expected from boundary vintage and the creation of newer districts. Thirty points do not match a current district polygon, including the five outside the current state polygon and boundary/version gaps. Modeling must retain both the source field and the spatial assignment with boundary-version metadata; it must not silently substitute one for the other.

### Pilot-zone assignment

Exactly 60 records fall inside the union of the 25 pilot polygons:

| Zone | Count | Zone | Count | Zone | Count | Zone | Count | Zone | Count |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| A01 | 0 | A02 | 0 | A03 | 7 | A04 | 0 | A05 | 0 |
| B01 | 4 | B02 | 2 | B03 | 3 | B04 | 2 | B05 | 1 |
| C01 | 3 | C02 | 3 | C03 | 1 | C04 | 1 | C05 | 2 |
| D01 | 2 | D02 | 11 | D03 | 2 | D04 | 4 | D05 | 3 |
| E01 | 4 | E02 | 1 | E03 | 1 | E04 | 1 | E05 | 2 |

At 30 m, all 2,046 valid source records, before state clipping, occupy 1,865 cells; 122 cells contain more than one record and the maximum is nine. The 303 Aizawl records occupy 287 cells. The 60 pilot records occupy 59 cells. At 90 m, the corresponding occupied-cell counts are 1,804 before state clipping, 275 in Aizawl, and 58 in the pilot. A Phase 5B manifest must reproduce these audit counts, then separately report the final state-clipped grid and transform.

### Attributes and missingness

The saved record payload contains 23 fields. Potentially relevant fields have the following completeness:

| Attribute | Nonblank | Missing | Audit interpretation |
| --- | ---: | ---: | --- |
| Coordinates / latitude / longitude | 2,046 | 0% | Presence location; label geometry |
| State | 2,046 | 0% | Filter/context, not predictor |
| Source-reported district | 2,046 | 0% | Grouping/audit field, not direct predictor |
| `geology` | 2,024 | 1.08% | Point-description text with 231 values; not a wall-to-wall predictor and unsafe to transfer to backgrounds |
| `activity` | 2,007 | 1.91% | Inventory outcome metadata; forbidden as predictor |
| `triggering` | 1,833 | 10.41% | Post-occurrence/interpretive label metadata; forbidden as predictor |
| `slide_name` | 500 | 75.56% | Identifier/description only |
| `source` | 4 | 99.80% | Four `PDLS` values; inadequate validation metadata |
| `check_stat` | 0 | 100% | No field-validation status available |
| `village` | 0 | 100% | Unavailable |
| `class_type`, landslide class/type/description fields | 0 | 100% | Unavailable in saved payload |
| `reactivati` | 157 meaningful values; 1,885 zero | 92.33% meaningful | Reactivation-year tags, not initial event dates |
| `reactiva_1`, `reactiva_2` | 2 meaningful values each; 2,040 zero | 99.90% meaningful | Sparse reactivation tags; one malformed-looking multi-year value |

The service schema has 134 fields, while the saved retrieval selected a smaller set. Phase 5B should re-query only fields needed for auditability, preserve stable source identifiers if permitted, and record field completeness. No source attribute should become a predictor merely because it is present on an occurrence record.

### Date audit and consequences

All six plausible service date fields—`date`, `date_acc`, `date_and_t`, `datetimety`, `exactdatei`, and `history_da`—contain zero usable values. The 157 reactivation-year tags describe reactivation or survey context and are not occurrence timestamps. The truthful result remains **2,046 geolocated records and zero usable event dates**.

This prevents:

- temporal train/test validation;
- linking a failure to antecedent or event rainfall;
- testing forecast lead time;
- estimating event rates through time; and
- a historical-event timeline with truthful dates.

It does not by itself prevent a static spatial susceptibility experiment. Such an experiment can use occurrence locations with static covariates and background samples, provided its spatial validation and presence-background limitations are explicit.

### Provenance, license, and quality limits

The snapshot records the GSI BhooSanket layer URL, query filter, pagination, declared CRS, and retrieval result. It does not record an explicit license, redistribution permission, model-training permission, mapping scale, survey protocol, inventory completeness, or positional accuracy. Four records identify `PDLS`; the remaining source field is blank. The completely blank `check_stat` field cannot substantiate individual field validation.

Before Phase 5B data preparation, the project must obtain and archive authoritative license/terms evidence and decide whether source records or derived training artifacts may be redistributed. If permission is unclear, raw and derived label artifacts must remain outside Git and outside deployment bundles.

## Predictor-data inventory

The table separates native datasets from derived summaries. “Absent” means no usable wall-to-wall asset was found anywhere in the local checkout, including ignored files.

| Candidate | Source | Provenance | Coverage | CRS | Native resolution | Temporal coverage | Repository / deployment status | Missingness | Licensing recorded | ML suitability | Leakage risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Elevation | Copernicus DEM GLO-30 DSM | REAL_DEM | Aizawl processing extent only | EPSG:4326 source | ~30 m; 342×342 source grid | Static | Metadata, zonal JSON, and visual Terrarium tiles committed and bundled; original GeoTIFF absent/ignored | 0% within recorded source extent; no statewide coverage | Attribution recorded; full terms not archived | Conditionally usable after reproducible statewide acquisition | Low; derived summaries can leak folds if computed globally with labels, though terrain itself does not |
| Slope | Horn derivative of GLO-30 | DERIVED from REAL_DEM | 25-zone pilot | EPSG:32646 processing | Derived at 30 m, then aggregated per zone | Static | Only zone mean/min/max/median/p90 statistics committed | No pilot nodata; absent statewide and no cell raster | Inherits DEM terms | Unusable as 25-row training data; recompute statewide at cell scale | Low if computed label-independently |
| Aspect | DEM derivative | DERIVED from REAL_DEM | 25-zone pilot | EPSG:32646 processing | 30 m derivative, only circular zone mean retained | Static | Zonal JSON only | No pilot nodata; absent statewide | Inherits DEM terms | Recompute statewide; encode sine/cosine | Low |
| General curvature and `tpi_3x3_m` | None prepared | Absent / proposed derivative | None | Not applicable | Not applicable | Static | Absent | 100% unavailable | Would inherit DEM terms | Conditionally usable after the fixed derivation below | Correlated-feature interpretation risk |
| Geology/lithology map | None | Absent | None | Not applicable | Not applicable | Static | Absent | 100% unavailable | Unknown | Unusable until acquired and licensed | GSI point `geology` text would leak inventory selection and is not valid coverage |
| Land cover / vegetation / NDVI | None | Absent | None | Not applicable | Not applicable | Static or climatology | Absent | 100% unavailable | Unknown | Unusable until acquired and time basis declared | Post-event imagery or date-mismatched imagery could leak/change labels |
| Soil type | None | Absent | None | Not applicable | Not applicable | Static | Absent | 100% unavailable | Unknown | Unusable until acquired | Low if independently mapped |
| Drainage / distance to stream | No stream network or hydrography raster | Absent | None | Not applicable | Not applicable | Static | Absent | 100% unavailable | Unknown | Conditionally usable after independent acquisition/derivation | Inventory access bias if streams were mapped during landslide surveys |
| Road distance / hill-cut proxy | Cached OSM road snapshot | REAL_OSM / derived | Detailed Aizawl pilot only | GeoJSON coordinates assumed EPSG:4326 | Vector mapping resolution; no uniform native cell size | Static snapshot | Committed/bundled and available to runtime | Unknown mapping completeness | OSM attribution present; ODbL compliance must be documented for training outputs | Sensitivity feature only, not minimum model | High access/reporting bias; roads also change after events and are used for exposure |
| Long-term rainfall / climatology | None | Absent | None | Not applicable | Not applicable | Required climatology | Absent | 100% unavailable | Unknown | Unusable until a consistent historical aggregate is acquired | Event-linked or recent rainfall would mix trigger with susceptibility |
| GPM IMERG observations | NASA GPM via cached retrieval | REAL_GPM | Aizawl pilot; only four native cells mapped to 25 zones | Geographic grid | ~0.1° / ~10 km | Three daily observations | Committed/bundled; runtime input | No reported gaps in tiny snapshot; no historical label alignment | Provider attribution recorded; terms not archived | Unusable as static susceptibility predictor | Severe temporal leakage/misalignment if paired with undated occurrences |
| SMAP soil moisture | NASA SMAP cached snapshot | REAL_SOIL_MOISTURE | Aizawl pilot; four cells mapped to zones | Native equal-area EPSG:6933 before mapping | ~9 km | One representative three-hour snapshot | Committed/bundled; runtime input | No reported gaps in snapshot; no historical label alignment | Provider attribution recorded; terms not archived | Unusable as static susceptibility predictor | Severe temporal leakage/misalignment |
| ECMWF forecast | ECMWF/Open-Meteo cached response | REAL_FORECAST | Aizawl pilot; two unique model grid cells for 25 zones | Geographic service grid | ~9 km | Three forecast days | Committed/bundled; runtime context | No reported gaps in snapshot | Terms not archived | Unusable as static susceptibility predictor | Future/current trigger data cannot describe undated historic labels |
| 25-zone terrain/weather statistics | TerraSense aggregation | DERIVED, mixed real/sample depending field | Pilot only | Polygon output in EPSG:4326; terrain processed in EPSG:32646 | One row per zone; not native raster resolution | Mixed static and current snapshots | Committed/bundled/runtime | Complete for 25 zones | Inherits sources | Unusable as 25 training rows | Aggregation, tiny sample, and current-trigger leakage |
| Settlements, facilities, exposure/access | Cached OSM and derived clipping | REAL_OSM / DERIVED | Pilot only | GeoJSON EPSG:4326 assumption | Vector | Cached snapshot | Committed/bundled/runtime | Mapping completeness unknown | OSM compliance must be documented | Exclude from susceptibility training | Post-event/exposure and reporting/access bias |
| Sample fixtures and fallback grid values | Repository fixtures | SAMPLE_MOCK / PROTOTYPE | Pilot/tests | Mixed declared geometry | Zone-level | Synthetic/static fixture | Committed for fallback/tests | Designed completeness | Repository-owned fixture | Forbidden for model training/evaluation | Direct synthetic-label and prototype-score leakage |

No local GeoTIFF, VRT, IMG, shapefile, GeoPackage, Parquet, NetCDF, or HDF predictor asset was found. The original Aizawl DEM checksum is recorded, but the file itself is absent. Terrarium PNG tiles are a visualization product and must not become the canonical training raster.

The DEM states are intentionally distinct: committed and deployable data consist of metadata, 25-zone terrain summaries, and visualization tiles; the recorded original Aizawl GeoTIFF is excluded by repository/deployment rules and is not present in this checkout; and a statewide source or derivative raster is absent. An ignored filename or recorded checksum does not make a raster available to training or deployment.

## Feature taxonomy

### Static susceptibility candidates

- Elevation and independently derived terrain shape: slope, aspect sine/cosine, general curvature, and the fixed `tpi_3x3_m` definition below.
- Wall-to-wall geology/lithology, land cover/vegetation climatology, soil class, and drainage-distance only after spatial coverage, vintage, license, and missingness are audited.
- Distance to roads only as a separately reported sensitivity analysis because it can proxy both hill cutting and survey/access bias.

### Dynamic trigger candidates

- Recent and antecedent GPM rainfall.
- Current SMAP soil wetness.
- Forecast rainfall.

These belong in a later trigger model. With zero event dates, the present GSI labels cannot be aligned to them.

### Exposure/access fields

Roads, settlements, communities, facilities, and access summaries describe what may be exposed and how responders may reach it. They are not landslide labels and are excluded from the susceptibility model.

### UI/context fields

Zone ID, district labels, state names, current selections, visual risk categories, provenance labels, and map-view state are presentation or grouping fields. They must not enter the feature matrix. The current prototype score, its category, its component contributions, and any future priority score are explicitly forbidden features.

## Spatial sample feasibility

| Training unit | Assessment |
| --- | --- |
| 25 pilot zones | **Rejected.** Twenty-five rows cannot support the proposed feature count, spatial validation, or credible generalization. Four zones contain no mapped presences, but those are not verified negative zones. |
| Aizawl raster cells/terrain units | Possible as a limited exploratory study after restoring the source raster. Only 303 current-boundary points and 287 occupied 30 m cells are available; inventory clustering and boundary mismatch constrain validation. Not preferred for the first model. |
| Mizoram-wide raster cells/terrain units | **Recommended.** It uses 2,041 state-contained records and statewide environmental variation. It requires acquiring a reproducible statewide predictor stack first. |
| District rows | **Rejected.** Eleven aggregate rows erase terrain variation and cannot support validation. Districts are useful as grouping/holdout units. |
| Landslide points plus sampled backgrounds | **Recommended label design.** Deduplicated occupied cells are presences; independently sampled cells are background or pseudo-absence samples, never confirmed non-landslides. |

### Proposed analysis grid

- **Extent:** the versioned Mizoram boundary, with a small raster-processing halo sufficient for terrain kernels, then clipped back to the study area for sampling and output.
- **CRS:** EPSG:32646 (UTM zone 46N), which contains the complete audited 91.604533–93.394447° E extent within its 90–96° E zone and provides one metric coordinate system for cell indexing, buffers, and distances.
- **Resolution:** 90 m for the first model, aligned to an explicitly stored grid origin. The approximately 30 m DEM should be area-aggregated onto that grid before derivatives are computed. Ninety metres reduces compute, duplicate-cell inflation, and implied precision relative to a 30 m model when hundreds of coordinates are rounded to 0.01°. It does not cure kilometre-rounded coordinates, so precision-stratified sensitivity remains required.
- **Sensitivity runs:** repeat core evaluation at 30 m if compute permits and after filtering/coarsening low-precision labels. Compare 90, 250, and 500 m presence-exclusion buffers because label accuracy is undocumented.
- **Nodata:** create a joint valid-data mask before sampling. Do not impute spatial holes across water/outside-coverage areas. Within valid coverage, declare any feature-specific imputation and fit it inside each training fold only.

At 90 m, the existing labels occupy exactly 1,804 cells before state clipping and final quality rules. The final presence count will be lower after exact/near-duplicate consolidation, state clipping, common-valid-mask filtering, and coordinate-precision sensitivity exclusions. The dataset manifest must report every reduction rather than promising a fixed training count in advance.

Statewide modeling is preferred because it uses the broadest available occurrence inventory and environmental range and permits meaningful current-district holdouts. The 25-zone grid supplies only 25 aggregate polygons and 60 occurrence records; treating the polygons as training rows would create a tiny, spatially dependent sample. Aizawl-only training would also discard most labels and narrow the transfer domain.

### Presence and background construction

The proposed labels are **presence versus sampled background**, not positive versus negative ground truth. “Presence cell” below means that at least one inventory record maps to the cell; “background cell” means only that it was sampled from the eligible, unlabeled study area.

1. Transform source coordinates into the fixed grid CRS and retain original values and precision metadata.
2. Remove exact duplicate records from model weighting while retaining a duplicate-count audit field.
3. Assign at most one presence label per analysis cell. Perform a sensitivity pass that clusters points within 30 m and another that excludes or coarsens visibly rounded coordinates.
4. Exclude background candidates within an initial 150 m of any retained presence. Re-run evaluation at 90, 250, and 500 m exclusion distances.
5. Draw spatially balanced backgrounds from the common predictor-valid mask, stratified by spatial block and, where defensible, broad elevation bands. Start with five backgrounds per presence and repeat sampling with at least five fixed seeds.
6. Never describe background cells as observed non-landslides. Inventory omission, inaccessible terrain, and incomplete mapping mean an unlabeled cell can contain an unrecorded landslide.

Roadside surveying, settlement access, differing district campaigns, boundary changes, duplicate reports, and coordinate rounding can all bias apparent susceptibility. Road distance may be used to quantify or stratify reporting bias, but promoting it to a causal terrain predictor would entangle the target with the collection process.

## Validation design

Simple random row splitting is prohibited as the primary result because adjacent cells share terrain and reporting processes.

### Spatial validation protocol

1. Estimate empirical spatial autocorrelation of labels and major predictors without consulting model performance. Start with 10 km square blocks in EPSG:32646; test 5, 10, and 20 km blocks and choose a preregistered size at or above the observed practical correlation range.
2. Use grouped spatial block cross-validation for inner model selection. Assign whole blocks to folds with a deterministic algorithm and record the block map and seed.
3. Use geographic outer evaluation. Prefer leave-one-current-district-out results across the 11 spatially assigned districts; all contain at least 75 audited records. Also report pooled held-out predictions. The 30 district-unassigned points must be excluded from district evaluation or placed in a separately declared spatial block.
4. Apply a minimum 1 km train/validation buffer around validation presences and report sensitivity to the buffer. Remove both presences and backgrounds in the buffer from training to limit near-neighbor leakage.
5. Generate background samples and any preprocessing parameters within the relevant training partition. Do not allow the same background location, duplicate cluster, or adjacent buffered cell into both training and validation.
6. Fix and publish independent seeds for grid/block assignment, each background replicate, hyperparameter search, and model fitting.

### Metrics and uncertainty

**Primary metric:** spatial-fold PR-AUC, because the operational sample is imbalanced and ranking presences above sampled background is the central first-stage task. Its absolute value depends on the declared background ratio, so it must be reported with that ratio and across background replicates. Handle the chosen five-to-one imbalance using training-fold sample/class weights where supported; tune or fix those weights inside inner folds and never rebalance the outer evaluation fold.

Secondary metrics are ROC-AUC, balanced accuracy, precision and recall at thresholds selected only within training folds, confusion matrices, spatial-fold distributions, and district-held-out distributions. Report median, interquartile range, full fold range, and bootstrap intervals based on spatial blocks rather than independent cells.

Brier score and calibration curves may be computed only as diagnostics against the declared sampled-background target. They do not establish real-world landslide probability because true absence and population prevalence are unknown. If calibration is attempted, compare sigmoid and isotonic methods inside inner spatial folds and evaluate the chosen method only on untouched outer folds. Until held-out spatial calibration and prevalence semantics are adequate, all public/API probability and confidence terminology remains forbidden.

## Proposed model comparison

### Candidate feature set

The first comparison should use the same versioned terrain matrix for every model:

- **Elevation (`elevation_m`):** area-weighted mean elevation in each 90 m cell, retaining broad topographic position.
- **Slope (`slope_deg`):** Horn 3×3 slope in degrees computed from the 90 m elevation grid, representing local gradient.
- **Aspect (`aspect_sin`, `aspect_cos`):** sine and cosine of Horn aspect so that north is not split across a 0°/360° discontinuity; flat cells use a declared neutral/missing rule fixed before fitting.
- **General curvature (`curvature_laplacian_per_m`):** the central-difference elevation Laplacian `(zE - 2zC + zW)/90² + (zN - 2zC + zS)/90²`, in inverse metres, retaining signed local convexity/concavity.
- **Terrain-position index (`tpi_3x3_m`):** centre-cell elevation minus the arithmetic mean of the eight immediately adjacent 90 m cells. The 3×3 footprint is 270 m by 270 m. Require all eight neighbors; otherwise mark nodata rather than filling across the edge.

This fixes one terrain-position measure rather than treating roughness and TPI as interchangeable candidates. These derivatives capture distinct representations of height, gradient, orientation, curvature, and local relative position, while their correlation must still be measured and reported.

Geology/lithology, land cover, soil, drainage-distance, and climatology should enter later ablations only after acquisition and audit. Road distance belongs in a reporting-bias sensitivity analysis. Dynamic rainfall, soil wetness, forecast values, prototype scores/categories/contributions, source district as a feature, zone IDs, GSI triggering/activity/geology text, roads/facilities/settlements/exposure, and post-event descriptions are forbidden.

### Models

1. **Regularized logistic regression:** transparent reference with standardized continuous variables and prespecified nonlinear terms only where justified. It establishes whether complex learners improve spatial generalization.
2. **Tree-based baseline:** a constrained random forest with bounded depth, minimum leaf size, and feature subsampling.
3. **XGBoost:** evaluate only after the final presence count and predictor matrix pass quality gates. Bound depth to shallow trees, use learning-rate/estimator tradeoffs, row/column subsampling, minimum child weight, regularization, and early stopping. Search ranges must be fixed before viewing outer-fold results.

The initial inner-fold search boundaries are deliberately finite: logistic-regression inverse regularization `C` from `0.001` through `100` on a logarithmic grid with L2 as the required reference; random forest 200–800 trees, depth 3–12, minimum leaf size 10–100, and feature fractions `sqrt`, 0.5, or 1.0; and XGBoost depth 2–6, learning rate 0.01–0.20, at most 2,000 boosting rounds with early stopping, row and column subsampling 0.6–1.0, minimum child weight 1–20, `gamma` 0–5, L1 regularization 0–5, and L2 regularization 1–20. Phase 5B may narrow these ranges from computational evidence before fitting, but may not expand or revise them after viewing outer-fold results without declaring a new experiment.

Where domain direction is sufficiently defensible, monotonic constraints may be tested—for example, slope over a restricted physical range—but they should not be imposed blindly because very steep bare cliffs, DEM artifacts, and nonlinear material effects can violate simple monotonic assumptions.

Model selection should maximize median outer spatial PR-AUC subject to stability across districts and background replicates. Prefer the simpler model when performance is within one standard error or when the complex model's gains concentrate in one district. All preprocessing, feature selection, calibration, and hyperparameter selection belong inside inner spatial folds.

### Explainability

No feature-importance or SHAP graphic should exist before a validated model exists. For a selected tree model, compute SHAP values only for held-out predictions, using a training-fold background sample. Produce:

- global held-out mean absolute SHAP values with fold variability;
- dependence plots for prespecified features;
- local explanations for selected held-out cells with feature values and provenance; and
- a stability table across districts and background replicates.

Correlated DEM derivatives can divide or swap attribution. SHAP values describe the fitted model, not physical causality. Local explanations must identify the model version, fold/holdout status, feature snapshot, and whether calibration was applied.

## Static, dynamic, exposure, and operational-risk separation

```text
Static susceptibility (slow-changing terrain/environment)
                         ┐
Dynamic trigger (rainfall, soil wetness, forecast) ──> future fusion ──> operational risk
                         ┘                                      │
Exposure/access (roads, settlements, facilities) ──────────────┘
```

- **Static susceptibility** ranks terrain/environmental predisposition and changes only when source layers or the validated model change.
- **Dynamic trigger** represents current and antecedent hydro-meteorological conditions. The existing prototype score combines these transparently; a trained trigger model is impossible with the undated GSI inventory.
- **Exposure/access** describes mapped people/assets/access context and does not train the susceptibility model.
- **Final operational risk** is future work that would combine validated susceptibility, trigger evidence, uncertainty, and exposure/priority rules. It must preserve the distinction between hazard, exposure, access, and confidence.

The trained susceptibility output must not replace the existing current-risk contract (`/risk/{zone_id}/current`, sometimes shortened to `/risk/current`) during Phase 5B. A future experimental contract should be separate and versioned, for example:

```json
{
  "readiness": "EXPERIMENTAL",
  "model": {"name": "terrain_susceptibility", "version": "...", "artifact_sha256": "..."},
  "output": {"relative_score": 0.0, "class": "...", "is_probability": false},
  "calibration": {"status": "NOT_CALIBRATED", "method": null},
  "validation": {"status": "SPATIAL_VALIDATION_PENDING", "design": "...", "metrics_ref": "..."},
  "features": [{"name": "slope", "source": "Copernicus GLO-30", "version": "..."}],
  "data_timestamp": null,
  "explanation": {"status": "UNAVAILABLE_UNTIL_HELD_OUT_VALIDATION", "values": []},
  "limitations": ["Presence-background relative susceptibility; not an event forecast"]
}
```

Static inputs may use acquisition/version dates, but a static model should not imply a current observation timestamp. Proposed output remains **experimental relative susceptibility** unless later spatial validation and calibration justify stronger terminology for a separately reviewed use case.

## Reproducible training and inference architecture

### Proposed paths for Phase 5B

These paths are a design only and are not created by Phase 5A:

```text
ml/susceptibility/
  README.md
  config/terrain_v1.yaml
  prepare_inventory.py
  prepare_grid.py
  extract_features.py
  make_spatial_splits.py
  sample_background.py
  train_baselines.py
  train_xgboost.py
  calibrate.py
  evaluate.py
  explain.py
  manifests.py
ml/tests/susceptibility/
  test_inventory.py
  test_grid_alignment.py
  test_spatial_splits.py
  test_no_leaky_features.py
  test_manifests.py
data/manifests/susceptibility/
  gsi_inventory_<version>.json
  predictor_stack_<version>.json
  dataset_<version>.json
  splits_<version>.json
artifacts/ml/susceptibility/<model-version>/
  model.*
  preprocessing.*
  model_manifest.json
  evaluation.json
  calibration.json
  explanations.*
  susceptibility.tif
```

Training outputs and source rasters should be ignored artifacts or external versioned objects unless license and size review explicitly approve a small file for Git. Manifests may be committed when they contain checksums, source URLs/identifiers, licenses, acquisition times, CRS/transforms, software versions, seeds, commands, feature schema, row-reduction counts, and artifact references without redistributing restricted data.

### Deterministic pipeline

1. Verify every source checksum and license gate.
2. Normalize labels while preserving original records; derive precision, duplicate-cluster, boundary assignment, and exclusion-reason fields.
3. Build the fixed EPSG:32646/90 m grid and common-valid mask.
4. Derive features from source rasters with declared resampling: bilinear/area aggregation for continuous elevation where justified, circular handling for aspect, and nearest/mode for categorical rasters.
5. Materialize immutable dataset and feature manifests before sampling.
6. Create spatial blocks, district holdouts, buffers, and repeated background samples using recorded seeds.
7. Fit preprocessing and baselines inside folds; run bounded XGBoost search only if its gate passes.
8. Generate untouched outer-fold predictions, metrics, calibration diagnostics, and held-out explanations.
9. Select a model by the preregistered rule, serialize it, and produce checksummed model/evaluation manifests.
10. Run an independent reproducibility command that rebuilds manifests and verifies hashes before any integration proposal.

### Compute and deployment

A 90 m statewide grid is expected to contain a few million candidate cells. A compact float32 feature stack is practical on a workstation; allow roughly 2–8 GB RAM for raster processing and tabular overhead. The sampled training matrix—approximately several thousand presences plus a bounded background multiple—is much smaller. A 30 m statewide stack would contain roughly an order of magnitude more cells and should be tiled/windowed rather than loaded wholesale.

Full training should run locally or on a pinned batch/CI workflow with artifact storage, not in ordinary pull-request CI and never in a Vercel request. Normal CI should run unit tests, tiny synthetic fixtures, manifest/schema checks, leakage guards, and a deterministic miniature end-to-end test.

Shipping Rasterio, XGBoost, SHAP, full raster stacks, and explanation assets in the current Vercel FastAPI deployment would increase package size, build complexity, and cold-start cost. Phase 5B should measure the then-current platform constraints instead of assuming a fixed limit. The safer first delivery is an offline precomputed susceptibility raster/tile or zone-summary artifact with a small manifest. If point inference later becomes necessary, use a small verified artifact in FastAPI only after bundle and latency testing, or a separate inference service.

If the experimental artifact is missing, corrupt, incompatible, or fails its checksum, the application must return an explicit unavailable experimental status. The current prototype scorer remains the operational fallback and must not silently relabel its output as ML. The hierarchy file/PostGIS abstraction remains unchanged because susceptibility artifacts are independent, versioned products rather than hierarchy storage.

## Go/no-go decision

### Decision: CONDITIONAL GO

The occurrence count supports an experiment, but the current checkout cannot yet support an honest trained model. The following gates are mandatory:

| Gap | Can existing local data solve it? | Required action |
| --- | --- | --- |
| GSI training/redistribution license absent | No | Obtain and archive authoritative terms or written permission; define what may be committed/deployed |
| Mizoram-wide DEM absent | No; only Aizawl derivatives are committed | Reproducibly acquire GLO-30 coverage for all Mizoram and verify license/checksums |
| Analysis-ready cell predictors absent | Partly after DEM acquisition | Derive aligned terrain features and manifests in EPSG:32646 |
| Mixed coordinate precision and unknown accuracy | Partly | Create precision strata, deduplicate, use coarser grid/buffers, and report sensitivity; source accuracy may remain unknown |
| Presence-only/reporting bias | Partly | Spatially balanced repeated background sampling, bias sensitivity, and truthful claims; cannot manufacture negatives |
| Static geology/land cover/soil/drainage/climatology absent | No | Defer from terrain-only v1 or acquire separately with license/version audit |
| Event dates absent | No in current GSI source | Do not build a historical trigger model; acquire a separately dated event catalog before any rainfall-linked training |
| ML libraries undeclared | Yes, after design approval | Add pinned training-only dependencies; avoid runtime dependency changes until inference design is approved |

The minimum viable feature set is terrain-only: `elevation_m`, `slope_deg`, `aspect_sin`, `aspect_cos`, `curvature_laplacian_per_m`, and `tpi_3x3_m`, derived from one versioned statewide DEM using the definitions above. Aizawl-only training is not recommended as the primary model. Mizoram-wide training provides far more presences, environmental diversity, and meaningful district-held-out evaluation. Aizawl should remain a secondary holdout/reporting geography.

The first model could support a statement such as: “experimental relative terrain susceptibility under a presence-background sampling design, validated with spatial holdouts.” It could not support occurrence probability, real-time risk, event prediction, forecast lead time, causal attribution, current road passability, verified blockage, or complete landslide absence in low-scoring cells.

## Exact Phase 5B implementation plan

Phase 5B may start only after its gate record contains: (1) confirmed GSI model-training rights; (2) confirmed GSI source and derived-data redistribution rules; (3) the authoritative source URL or identifier, source version and a UTC retrieval date—if the provider publishes no version, record that fact and checksum a complete layer-metadata response; (4) a reproducible statewide DEM acquisition procedure; (5) confirmed DEM licensing and required attribution; and (6) SHA-256 manifests for every raw source and derived dataset. Public accessibility alone satisfies none of the licensing items. No trained-model publication may occur until all blocking gates are resolved.

1. **License gate:** record GSI and Copernicus terms, redistribution/training decisions, attribution text, source URL/version/retrieval date, and restricted-artifact handling. Stop Phase 5B if GSI model use or redistribution rules cannot be established.
2. **Inventory snapshot:** reacquire an immutable, minimally necessary GSI snapshot with stable identifiers and audited schema fields; hash it and reproduce all Phase 5A counts. Preserve 2,046 raw records, zero usable dates, and every exclusion reason.
3. **Statewide DEM:** acquire complete Mizoram GLO-30 tiles, record tile IDs/checksums/version, mosaic only in the build workspace, and establish a buffered EPSG:32646 grid aligned at 90 m.
4. **Feature build:** derive the fixed six-field terrain set—`elevation_m`, `slope_deg`, `aspect_sin`, `aspect_cos`, `curvature_laplacian_per_m`, and `tpi_3x3_m`—exactly as defined above, with edge/nodata tests. Produce checksummed raw-source and derived-predictor manifests. Do not add absent environmental layers opportunistically.
5. **Label build:** state-clip, consolidate exact duplicates, assign one presence per cell, retain count/precision metadata, and emit precision/near-duplicate sensitivity cohorts.
6. **Background and splits:** implement 150 m default exclusion with 90/250/500 m sensitivity; five backgrounds per presence by default; at least five seeds; 10 km initial spatial blocks; measured 5/10/20 km autocorrelation sensitivity; 1 km train/validation buffer; current-district outer holdouts.
7. **Leakage tests:** fail the pipeline if dynamic weather, prototype risk outputs, GSI post-event attributes, IDs/geographies, exposure/access fields, or samples enter the matrix. Verify no cell/cluster/buffer overlap across folds.
8. **Baselines:** train regularized logistic regression and a bounded tree baseline with preprocessing entirely inside inner folds. Publish spatial metrics and fold variability before deciding whether XGBoost is warranted.
9. **XGBoost gate:** add pinned training-only XGBoost dependencies and a bounded search only if sample/feature quality and baseline results pass. Use early stopping and the one-standard-error simplicity rule.
10. **Calibration assessment:** compare sigmoid and isotonic only within nested spatial validation; retain `NOT_CALIBRATED` and `is_probability=false` unless held-out evidence and target prevalence semantics justify otherwise.
11. **Evaluation and explanations:** create spatial/district results, background-replicate uncertainty, held-out SHAP outputs for the selected tree model, and correlated-feature cautions.
12. **Artifact review:** serialize model/preprocessing plus dataset, split, evaluation, and model manifests; reproduce checksums in a clean environment. Keep large/restricted artifacts out of Git.
13. **Integration proposal:** only after review, propose a separate experimental API contract and offline inference product. Do not replace the existing prototype current-risk route. Benchmark Vercel artifact size, package size, and cold start before choosing FastAPI inference; do not load statewide training rasters during a request.

### Proposed Phase 5B changed-file scope

Subject to the license gate, the intended change is limited to:

- new `ml/susceptibility/` pipeline/configuration modules listed above;
- new `ml/tests/susceptibility/` tests and tiny synthetic fixtures;
- a separate pinned training requirements file under `ml/`;
- source/dataset/model manifest JSON files under `data/manifests/susceptibility/` where redistribution permits;
- `.gitignore` additions for local rasters, prepared datasets, and model artifacts;
- focused documentation for reproduction and claims.

No frontend file, production risk route, hierarchy/PostGIS module, scoring configuration, deployment configuration, model artifact, raw raster, or generated susceptibility layer should change in the initial Phase 5B training PR. Any later experimental API integration should be a separate reviewed change.

## Data and claim limitations

- The GSI inventory is presence-only and may reflect where surveys and roads made reporting possible.
- Five points fall outside the current state geometry and 30 do not match current district polygons; boundary versions matter.
- Mixed coordinate precision and absent accuracy metadata limit cell-level certainty.
- Duplicate records and nearby records can represent repeat reports, separate failures, or coordinate rounding; the repository cannot distinguish these reliably.
- No usable dates exist, so current GPM, SMAP, and forecasts cannot be paired with failures.
- A terrain-only model omits material, drainage, land-cover, and long-term hydroclimatic controls.
- Presence-background discrimination is not an occurrence probability. Calibration against sampled backgrounds does not recover real prevalence.
- Spatial validation estimates transfer under the observed inventory and predictor domain; it does not validate future event timing.
- SHAP and feature importance explain model behavior, not causal mechanisms.
- Static susceptibility must remain separate from dynamic triggers and exposure/access.

Phase 5A therefore supports a later licensing and preparation phase for a controlled experiment. It does not claim that TerraSense has a trained susceptibility model, and it does not permit trained-model publication until the stated licensing, data, reproducibility, and spatial-validation gates are resolved.
