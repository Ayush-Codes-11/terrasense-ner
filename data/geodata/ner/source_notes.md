# Northeast India boundary source notes

## Selected source

- **Publisher/organisation:** geoBoundaries project (William & Mary GeoLab), using
  the source organisations declared in its release metadata.
- **State dataset:** geoBoundaries `gbOpen/IND/ADM1`, release commit `9469f09`.
  The release metadata names the DataMeet India community and Election Commission
  of India as the source.
- **District dataset:** geoBoundaries `gbOpen/IND/ADM2`, release commit `9469f09`.
  The release metadata names Pathways Data Pvt. Ltd. and
  [LGD Directory](https://lgdirectory.gov.in/) as the source.
- **Source references:**
  - [ADM1 metadata](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/)
  - [ADM2 metadata](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/)
  - [ADM1 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1.geojson)
  - [ADM2 GeoJSON](https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson)
- **Boundary vintages:** ADM1 metadata says 2011; ADM2 metadata says 2021.
  Both were built by geoBoundaries on 2023-12-12. The district release metadata
  reports 736 India-wide ADM2 units.
- **CRS:** Source geometries are geographic WGS 84 and outputs declare
  `EPSG:4326`.
- **Licence/access:** ADM1 is listed as CC BY 2.5 India, with DataMeet as the
  licence source. ADM2 is listed as Open Data Commons Open Database License 1.0,
  with Pathways Data as the licence source. Users of the data should retain
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

## Administrative-version comparison

The ADM2 source is explicitly LGD-derived and represents 2021. Within that
version, all 119 filtered district features are present in both the selected
boundary set and its source district list: no missing, extra, or renamed
districts were found. This is not a claim that the 2021 list is current in
2026. The LGD portal is authoritative for a newer live list, but its bulk
download/API was not machine-readable during preparation; therefore any
districts created, split, renamed, or reorganized after the 2021 source
vintage remain an unresolved administrative-version limitation and must be
rechecked before production integration.

