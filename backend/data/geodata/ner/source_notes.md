# Northeast India boundary source notes

## Selected source

- **Publisher/organisation:** geoBoundaries project (William & Mary GeoLab), using
  the source organisations declared in its release metadata.
- **ADM1 / state dataset:** geoBoundaries `gbOpen/IND/ADM1`, release commit
  `9469f09`. The release metadata names the DataMeet India community and
  Election Commission of India as the source.
- **ADM2 / district dataset:** geoBoundaries `gbOpen/IND/ADM2`, release commit
  `9469f09`. The release metadata names Pathways Data Pvt. Ltd. and
  [LGD Directory](https://lgdirectory.gov.in/) as the source.
- **Source references:**
  - [ADM1 metadata](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/)
  - [ADM2 metadata](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/)
  - [ADM1 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1.geojson)
  - [ADM2 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson)
- **Boundary vintages:** ADM1 = **2011**; ADM2 = **2021**. Both were built by
  geoBoundaries on 2023-12-12. The district release metadata reports 736
  India-wide ADM2 units.
- **CRS:** Source geometries are geographic WGS 84 and outputs declare
  `EPSG:4326`.
- **Licence/access:** ADM1 = **CC BY 2.5 India**. ADM2 = **Open Data Commons
  Open Database License 1.0 (ODbL 1.0)**. Users of the data should retain
  attribution and review the linked licence terms before redistribution.

## Selection rationale

This source was selected because its release metadata identifies government or
government-derived inputs (Election Commission of India and LGD Directory),
provides downloadable versioned GeoJSON, and exposes stable source feature IDs.
The downloaded features do not expose LGD numeric codes, so no LGD code has been
invented or inferred.

## Filtering and identifiers

The preparation script filters ADM1 using the eight ISO-like state identifiers
requested for this project, normalizes diacritics in state names, and assigns
each ADM2 feature to the NER state whose source ADM1 geometry covers its
representative point. District IDs are namespaced source IDs in the form
`IND-ADM2-<shapeID>`; the original `shapeID` is retained as
`source_feature_id`. `lgd_code` is explicitly `null`.

The region boundary is a dissolved union of the eight validated state
geometries. The raw 46 MB/48 MB source downloads are not committed; the script
downloads them on demand.

## Current LGD reconciliation attempt

Comparison date: **2026-09-11**.

The public [LGD district directory](https://lgdirectory.gov.in/globalviewdistrictforcitizen.do)
was checked on this date. Its page exposes the current state selector, including
all eight NER states, but the district report requires an interactive CAPTCHA
and session submission. No public machine-readable district export/API response
could be retrieved in this run. Consequently, the following are the honest
results:

- **2021 boundary districts confirmed current:** not determinable from the
  accessible LGD response; the 119 names remain the 2021 geometry baseline.
- **Current LGD districts missing from 2021 geometry:** not determinable.
- **2021 district names changed:** not determinable from the accessible
  current LGD district report.
- **Districts split/created after 2021:** not determinable from the accessible
  current LGD district report.
- **Unresolved mapping issues:** all current-list comparison items above, plus
  the absence of LGD numeric codes in the geometry features.

This is an explicit unresolved limitation, not a claim that the 2021 list is
current in 2026. A maintainer with an authenticated/manual LGD export must
complete the comparison before production use. The 2021 source-list comparison
itself remains internally consistent: 119 NER district geometries were
selected from the 2021 ADM2 release, with no duplicate source IDs.
