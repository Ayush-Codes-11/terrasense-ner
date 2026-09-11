# Phase 2 boundary handoff

## Selected source

The generated files use geoBoundaries `gbOpen` India releases at commit
`9469f09`:

- State source: `geoBoundaries-IND-ADM1.geojson`, boundary vintage 2011,
  source organisations DataMeet India community and Election Commission of
  India.
- District source: `geoBoundaries-IND-ADM2.geojson`, boundary vintage 2021,
  source organisations Pathways Data Pvt. Ltd. and LGD Directory.
- Build date in source metadata: 2023-12-12.
- Source references and licence notes: [source_notes.md](./source_notes.md).
- Output CRS: `EPSG:4326`.

The source was chosen over an unverified GitHub/Kaggle file because its release
metadata identifies its upstream organisations, provides versioned downloads,
and supplies stable source feature IDs. ADM2 features do not include LGD
numeric codes, so `lgd_code` is null throughout rather than guessed.

## Validation results

- Total NER states: **8**
- Total districts: **119**
- District count by state:
  - Arunachal Pradesh (`IN-AR`): 25
  - Assam (`IN-AS`): 33
  - Manipur (`IN-MN`): 16
  - Meghalaya (`IN-ML`): 11
  - Mizoram (`IN-MZ`): 11
  - Nagaland (`IN-NL`): 11
  - Sikkim (`IN-SK`): 4
  - Tripura (`IN-TR`): 8
- Duplicate state IDs: **0**
- Duplicate district IDs: **0**
- Null/empty geometries: **0**
- Invalid geometries: **0**
- Districts with missing state relation: **0**
- Geometry types: Polygon/MultiPolygon only
- Accidental whole-India features: **0**
- Aizawl present: **YES**
- Aizawl state relation: **`IN-MZ` / Mizoram**
- Aizawl canonical district ID: **`IND-ADM2-76128533B34203923268864`**
- LGD mapping status: **Not available in the selected geometry features;
  `lgd_code` is null for all districts. No numeric LGD code was guessed.**
- CRS: **EPSG:4326**

## Administrative-version comparison

The 119 districts are internally consistent with the selected geoBoundaries
ADM2/LGD-derived 2021 district list: no source-list omissions, additions, or
renames were found in the filtered NER set. The state source is a 2011
boundary vintage, while the district source is 2021; this mixed vintage is
documented and must not be interpreted as a single-date official snapshot.

The LGD portal remains the authoritative source for checking changes after
2021. A machine-readable current LGD export was not accessible during this
preparation, so post-2021 new/split/renamed districts are an unresolved
limitation and should be reconciled before production use.

## Files generated

- `ner_boundary.geojson` — dissolved NER region boundary.
- `states.geojson` — exactly the eight requested states.
- `districts.geojson` — exactly the 119 districts linked to those states.
- `metadata.json` — hierarchy metadata and exact Aizawl pilot ID.
- `source_notes.md` — source, licence, processing, and limitation notes.
- `PHASE2_BOUNDARY_HANDOFF.md` — this handoff.
- `scripts/prepare_ner_boundaries.py` — reproducible downloader, filter,
  spatial linker, writer, and validator.

The source downloads are intentionally excluded from the commit. Running
`py scripts/prepare_ner_boundaries.py` from the repository root downloads them
on demand and regenerates all GeoJSON and metadata outputs.

## Aizawl status

This handoff only supplies hierarchy and boundary data. It does not alter the
existing A01-E05 prototype grid or risk outputs. Backend integration should
use the exact Aizawl ID above and retain the requested status values:
`coverage_level=DETAILED_PILOT` and
`risk_model_status=STATIC_ML_VALIDATION_PENDING`.

## Git handoff

- Branch: `phase2/ner-boundary-data`
- Dataset commit hash: `fa1f17c`
- The final branch tip is supplied in the delivery message. Embedding a
  branch-tip hash in this file would itself create another commit and change
  that hash.
