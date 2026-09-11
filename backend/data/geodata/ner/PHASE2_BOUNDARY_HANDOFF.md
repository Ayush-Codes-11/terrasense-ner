# Phase 2 boundary handoff

## Selected source

The generated files use separate geoBoundaries `gbOpen` India releases at
commit `9469f09`:

- **ADM1 / state source:** `geoBoundaries-IND-ADM1.geojson`, boundary vintage
  **2011**, source organisations DataMeet India community and Election
  Commission of India, licence **CC BY 2.5 India**.
- **ADM2 / district source:** `geoBoundaries-IND-ADM2.geojson`, boundary vintage
  **2021**, source organisations Pathways Data Pvt. Ltd. and LGD Directory,
  licence **ODbL 1.0**.
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

## Boundary and administrative dates

- Boundary geometry vintage: **ADM1 = 2011; ADM2 = 2021**
- Administrative-list comparison date: **2026-09-11**

## Current LGD reconciliation results

The public [LGD district directory](https://lgdirectory.gov.in/globalviewdistrictforcitizen.do)
was checked on **2026-09-11**. The page exposed the current state selector and
all eight NER states, but the current district report required an interactive
CAPTCHA and session submission. No machine-readable current district export or
API response could be retrieved during this run.

Therefore:

| Requested comparison | Result |
|---|---|
| 2021 boundary districts still current | Not determinable from accessible current LGD response; 119-name 2021 baseline retained |
| Current LGD districts missing from 2021 geometry | Not determinable |
| 2021 district names changed | Not determinable |
| Districts split/created after 2021 | Not determinable |
| Unresolved mapping issues | Current-list comparison blocked by LGD CAPTCHA/session; geometry has no LGD numeric codes |

This is deliberately reported as unresolved. It must not be presented as proof
that the 2021 district list is current in 2026. The internal 2021 comparison
is complete: all 119 selected NER features have unique source IDs and valid
state relationships. A maintainer should obtain an authenticated LGD export and
complete the name/code crosswalk before production use.

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
- Dataset commit hash: superseded by the reconciliation update; final branch
  tip is supplied in the delivery message.
- The final branch tip is supplied in the delivery message. Embedding a
  branch-tip hash in this file would itself create another commit and change
  that hash.
