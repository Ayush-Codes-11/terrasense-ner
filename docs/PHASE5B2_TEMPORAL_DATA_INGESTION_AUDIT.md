# Phase 5B-2: Temporal Event Data, Automatic Ingestion, and Authority Operations Audit

**Audit date:** 2026-09-28

**Repository baseline:** `3fafa97cdeddf1755edcccfb09218eb0eec9e35a`

**Decision:** **NO-GO for temporal-trigger model training with currently verified data.**
**Architecture decision:** **CONDITIONAL GO for a source-authorized ingestion and authority-review foundation**

## Executive decision

TerraSense does not currently have enough legally usable, verified, spatially precise, timestamped Mizoram landslide events to train or validate a truthful dynamic trigger model.

The strongest immediately inspectable source is NASA COOLR Reports Points. Its current service contains 41 records assigned to Mizoram. All 41 have coordinates and 39 have a recorded event date. Only two locations claim exact spatial accuracy. Twelve records contain a clock-like value and one contains the literal value `unknown`, but the source time zone is undocumented. Therefore none can be treated as a verified exact instant. The records are useful for discovery, authority review, source reconciliation, and limited sensitivity analysis. They are not a sufficient temporal-training set.

The current repository GSI inventory remains 2,046 geolocated records with zero usable occurrence dates. It cannot support event-specific rainfall matching, temporal validation, forecast lead-time claims, or a historical-event timeline. Its training and redistribution rights remain unresolved. No GSI record may be given an inferred date.

NRSC reports 12,385 mapped Mizoram landslides, but those counts are seasonal or event-associated mapping outputs: 1,205 for monsoon 2014, 2,254 for monsoon 2017, and 8,926 for a 2017 event inventory. They are not 12,385 independently timestamped incidents. Bhuvan/NDEM conditions also block bulk coordinates, derivatives, redistribution, and automated retrieval without written authorization.

A 2026 Zenodo deposit describes 19 dated events in and around Aizawl. The deposit is CC BY 4.0, but it combines GSI, government, literature, and media sources. Record-level provenance and upstream rights require review before ingestion or training. Nineteen clustered events cannot validate a temporal model.

The practical next step is an official data-sharing agreement with Mizoram DMR/SEOC/DDMAs and GSI. It must provide immutable source identifiers, occurrence date/time with time zone and precision, coordinates with uncertainty, event type, evidence, verification decisions, update/correction lineage, training rights, and automated retrieval terms. Until those gates pass, no temporal trigger model should be trained or published.

This decision does not change Phase 5A static susceptibility. Static terrain modelling and dynamic trigger forecasting remain separate. Copernicus DEM remains static terrain data. Exposure, roads, facilities, alerts, and public field reports are not landslide labels.

## Governing facts carried forward

- The current GSI repository snapshot contains 2,046 geolocated Mizoram records and zero usable occurrence dates.
- The GSI snapshot must never receive fabricated dates, timestamps, or weather matches.
- GSI model-training and redistribution permission remains unresolved.
- The current risk score is a deterministic heuristic relative prototype score, not trained ML, probability, confidence, calibration, or a validated forecast.
- The prototype score uses slope, recent rainfall, antecedent rainfall, and soil wetness through fixed weights and normalization constants. It remains unchanged.
- Copernicus GLO-30 is a static terrain source. It is not a recurring weather or event feed.
- Static susceptibility asks where failure is more likely relative to other locations.
- Dynamic trigger modelling asks when observed or forecast hydro-meteorological conditions raise risk at susceptible locations.
- Exposure and access describe people, roads, settlements, and facilities. They are not event labels.
- The public field-report and alert routes are prototype, in-memory interfaces. They do not implement authority identity, durable review, or official warning delivery.

## Audit method and claim rules

The audit used primary organisation pages, primary licence text, official APIs, official data records, and peer-reviewed source publications. Search results were discovery aids only. A source is marked `BLOCKED_PENDING_PERMISSION` when training, automation, redistribution, or operational rights are absent or ambiguous.

The following rules govern every count:

1. A catalogue publication time is not an event occurrence time.
2. A portal update time is not an event occurrence time.
3. A rainfall peak is not an inferred event time.
4. A date-only record is not an exact-time record.
5. A clock value without a documented time zone is not an exact instant.
6. Seasonal imagery inventories are not collections of individually timed incidents.
7. A submitted citizen report is not an authority-verified event.
8. Absence of a record is not evidence that no landslide occurred.
9. Catalogue confidence, reliability, or source authority is not calibrated model confidence.
10. Raw source records remain immutable; corrections create new versions and lineage.

The deterministic machine-readable source registry is:

- `docs/manifests/susceptibility/temporal_event_source_registry.json`

It separates training, derivative, raw-redistribution, automated-retrieval, and commercial or operational permissions. Public availability is never treated as permission.

## Ranked source matrix

| Rank | Source | Verified useful counts | Time quality | Licence and automation | Decision |
| ---: | --- | --- | --- | --- | --- |
| 1 | Mizoram DMR/SEOC/DDMA verified incident records | No public structured count | Aizawl guidance requires date, time, and place; first-hand officer verification exists | No public dataset licence or feed | `BLOCKED_PENDING_DATA_SHARING_AGREEMENT`; preferred gold-label route |
| 2 | GSI BhooSanket | Repository: 2,046 geolocated, zero dates | Public form captures date/time, repository copy does not | Reproduction requires prior email permission; training/automation/redistribution unstated | `BLOCKED_PENDING_PERMISSION` |
| 3 | Aizawl 2016-2025 Zenodo research inventory | 19 events | Date-level; exact time and zone not established | Deposit CC BY 4.0; upstream GSI and record-level provenance unresolved | `BLOCKED_PENDING_PROVENANCE_REVIEW` |
| 4 | NASA COOLR Reports Points | Global 14,750; India 1,741; Northeast India 504; Mizoram 41 | 39 dates; zero verified exact instants | Reuse, derivatives, and redistribution explicitly permitted; recurring automation terms and rates unstated | Useful for discovery/review; insufficient for training |
| 5 | NASA COOLR Events Points | Global 40,154; India 176; Mizoram 0 | Event-dependent | Same NASA permission | No current Mizoram labels |
| 6 | UGLC 2026 | 1,061,450 global point records; Mizoram count not inspected | Heterogeneous and source-derived | CC BY-NC 4.0; operational/commercial use blocked | Non-commercial discovery/research only |
| 7 | NRSC Landslide Atlas | India 80,933; Northeast India 42,547; Mizoram 12,385 | Seasonal or event-window, not individual occurrence time | Bhuvan restrictions block bulk feeds, derivatives, and redistribution without authorization | `BLOCKED_PENDING_PERMISSION` |
| 8 | NDMA Sachet CAP | Official alerts, not event labels | Precise alert lifecycle times | Automated ETag consumption documented; training/reuse terms unstated | Operational context only |
| 9 | NASA GLC legacy export | One-time export current to 2016-03-07 | Heterogeneous | Legacy terms gate; superseded by current COOLR services | Do not ingest |
| 10 | Global Fatal Landslide Database | 4,862 global fatal events, 2004-2016 | Date-level; coarse positions | Article is CC BY; underlying database rights not established | Comparator only |
| 11 | DesInventar | No national India or Mizoram public database found | Database-dependent | Dataset rights belong to contributors | Unusable for Mizoram |
| 12 | IMD APIs | Weather only | Product timestamps | Data-reuse terms require confirmation | Future trigger predictor, never a label |
| 13 | Mizoram DIPR archive | No complete structured count | Publication time differs from occurrence time | No explicit reusable-data or automation permission | Official verification lead only |

Ranks indicate relevance to a future truthful Mizoram label set, not general scientific quality.

## Source findings

### Geological Survey of India: BhooSanket/Bhusanket

Primary pages:

- Terms: https://bhusanket.gsi.gov.in/terms.html
- Contact: https://bhusanket.gsi.gov.in/contactUs.html
- Public report form: https://bhusanket.gsi.gov.in/LandslideReport_new.html

GSI states that portal material may be reproduced after permission is obtained by email, must be reproduced accurately, and must acknowledge the source. The permission does not extend to third-party content. That is not an open licence and does not explicitly cover model training, transformed datasets, recurring API access, public repository storage, raw coordinate redistribution, model distribution, operational use, or publication of derived predictions.

The BhooSanket privacy page says GSI may use information supplied to its application for machine learning. That describes GSI's use of submitted data. It does not authorize TerraSense to train on GSI data.

The public report form demonstrates that GSI can capture date, time, location, type, damage, road blockage, photographs, and reporter details. It does not establish an export contract or the quality/completeness of the repository snapshot.

Required written request to `dir.ghrm.landslide@gsi.gov.in` and `nlfc.ghrm@gsi.gov.in`:

- Identify the exact product and version represented by the repository file.
- Request permission for model training and validation.
- Request permission to normalize, deduplicate, transform, and spatially join records.
- Request raw-coordinate public-repository and private-object-storage rules.
- Request raw and derived redistribution rules.
- Request permission to publish model artifacts, aggregate metrics, explanations, and map outputs.
- Request an automated recurring retrieval method, cadence, authentication, and rate limits.
- Request commercial, competition, research, and operational-use terms separately.
- Request positional accuracy, mapping scale, occurrence-time semantics, correction history, and provenance.
- Request a documented time-zone convention.

Until written permission exists, GSI remains a blocking gate.

### NRSC Landslide Atlas, Bhuvan, and NDEM

Primary pages:

- Atlas page: https://www.nrsc.gov.in/nrscnew/resources_atlas_landslide.php
- Atlas PDF: https://www.nrsc.gov.in/nrscnew/assets/pdf/atlas/landslide/Landslides_Atlas_of_India_Updated_25Aug2023.pdf
- NRSC site terms: https://www.nrsc.gov.in/nrscnew/termsConditions.php
- Bhuvan user agreement: https://bhuvan-app1.nrsc.gov.in/2dresources/documents/1_Bhuvan_User_Handbook.pdf

The atlas describes approximately 80,000 mapped landslides from 1998-2022 across 17 states and two union territories. The updated table totals 80,933. Summing the eight Northeast states yields 42,547; Mizoram contributes 12,385.

Mizoram's 12,385 comprises:

- 1,205 mapped for monsoon season 2014;
- 2,254 mapped for monsoon season 2017;
- 8,926 mapped in a 2017 event-based inventory.

Those are mapped failure features linked to seasons or trigger events. They do not supply an independent event timestamp for every mapped feature. Assigning a season start, image date, event publication date, or trigger date to every polygon would fabricate temporal precision and create leakage.

NRSC's general site terms permit non-commercial use of downloadable content with attribution and say users may create derivatives. The Bhuvan agreement is more restrictive: without written authorization, it prohibits copying or derivative works, redistribution, mass downloads or bulk feeds including coordinates, and database creation. The applicable data-access route and product-specific terms must be resolved in writing. TerraSense must not use general web terms to bypass Bhuvan/NDEM restrictions.

### NASA COOLR and GLC

Primary pages and services:

- NASA Landslide Reporter: https://science.nasa.gov/citizen-science/landslide-reporter/
- COOLR Reports Points item: https://gis.earthdata.nasa.gov/portal/home/item.html?id=b1b68a19b51342bf83260fbb3d9588f5
- COOLR Reports service: https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/COOLR_Reports_Points/FeatureServer
- COOLR Events Points item: https://gis.earthdata.nasa.gov/portal/home/item.html?id=521b98e18e684b529da498624c6335b2
- COOLR Events service: https://gis.earthdata.nasa.gov/portal/rest/services/Landslides/COOLR_Events_Points/FeatureServer
- Legacy GLC export: https://data.nasa.gov/dataset/global-landslide-catalog-export

Both current ArcGIS items publish NASA's Permission to Use, Reproduce, and Distribute. It grants worldwide reproduction, derivative-work, display, sublicensing, and distribution rights. Redistribution requires the permission notice, prominent modification notices, retained notices, and any applicable NOTICE attribution. It does not grant NASA trademarks and carries warranty/liability disclaimers. No service-level rate limit or recurring-harvest policy was found, so recurring automation remains `ambiguous_not_stated` pending NASA confirmation.

Current count-only queries on 2026-09-28 found:

| Layer/filter | Count |
| --- | ---: |
| COOLR Reports, global | 14,750 |
| COOLR Reports, India | 1,741 |
| COOLR Reports, eight Northeast states | 504 |
| COOLR Reports, admin division Mizoram | 41 |
| COOLR Reports, current Mizoram bounding box | 49 |
| COOLR Events, global | 40,154 |
| COOLR Events, India | 176 |
| COOLR Events, current canonical Mizoram polygon | 0 |

The bounding-box value 49 is not the Mizoram dataset count because it includes adjacent geography. The administrative filter's 41 records were inspected as a bounded regional subset.

For reproducibility, the Reports subset used layer `COOLR_Reports_Points/FeatureServer/0/query` with `f=json`, `where=country_code='IN' AND admin_division_name='Mizoram'`, `outFields=*`, `returnGeometry=true`, `outSR=4326`, and `resultRecordCount=100`. The count-only request to the same layer used that `where` expression and `returnCountOnly=true`; global and India counts used `where=1=1` and `where=country_code='IN'`, respectively, with `returnCountOnly=true`. The Events count used `COOLR_Events_Points/FeatureServer/0/query`, `f=json`, `where=1=1`, `geometryType=esriGeometryPolygon`, `spatialRel=esriSpatialRelIntersects`, `inSR=4326`, and `returnCountOnly=true`, with the current Mizoram ADM1 polygon supplied as the `geometry` parameter. That polygon is from `data/geodata/ner/states.geojson` (geoBoundaries gbOpen India ADM1, release `9469f09`, 2011 boundary vintage; file SHA-256 `8f1b1341d6cedd97eb5324cb6f4d73cddb8639822c73df8241fe6ca24bc73ec2`). A local WGS84 point-in-polygon check of the 41 Reports geometries found 41 strictly inside, zero on the boundary, and zero outside. `contains` was used for strictly inside; `covers` was used to check boundary-inclusive membership. The 41-report count is therefore consistent across administrative assignment and this boundary version. It should still not be read as complete Mizoram occurrence coverage. The count responses and bounded regional response are hashed in the evidence table below; these are catalogue reports, not 41 independently field-verified incidents.

#### Mizoram COOLR Reports quality

- 41 records; 41 valid point geometries.
- 39 non-null event dates; two undated.
- Earliest recorded date: 2007-07-30.
- Latest recorded date: 2021-06-12.
- 13 non-empty time values: 12 clock-like values and one literal `unknown`.
- No documented event-time time zone; zero verified exact instants.
- Zero exact-coordinate duplicate groups.
- Four same-date, within-10-km candidate pairs, representing two apparent clusters. They are review candidates, not automatic duplicates.
- Location accuracy: exact 2; 1 km 10; 5 km 12; 10 km 4; 25 km 7; 50 km 5; 100 km 1.

Recorded-date distribution:

| Year | Count | Year | Count |
| ---: | ---: | ---: | ---: |
| 2007 | 3 | 2015 | 9 |
| 2009 | 1 | 2016 | 2 |
| 2010 | 9 | 2017 | 8 |
| 2012 | 1 | 2018 | 2 |
| 2013 | 2 | 2021 | 1 |
| 2014 | 1 |  |  |

| Month | Count | Month | Count |
| ---: | ---: | ---: | ---: |
| April | 1 | August | 8 |
| May | 3 | September | 12 |
| June | 9 | October | 1 |
| July | 4 | November | 1 |

COOLR Reports combines Global Landslide Catalog imports and citizen submissions. Online news, reports, scientific sources, and user contributions introduce language, population, impact, media, and access bias. A NASA/LRC check is not the same as an official Mizoram field verification. These records should enter a human-review queue with their original source links and uncertainty.

The legacy GLC export was a one-time snapshot current through 2016-03-07 and required users to agree to export terms. The current COOLR services and their explicit item licences are the authoritative path.

### Aizawl 2016-2025 research deposit

Primary records:

- Zenodo: https://zenodo.org/records/20783995
- Metadata API: https://zenodo.org/api/records/20783995
- Author preprint: https://arxiv.org/abs/2606.23281

The version-1 Zenodo deposit, DOI `10.5281/zenodo.20783995`, is titled *Dataset for "Frictional timescales of landslides in Mizoram under climate extremes]{Frictional timescales and the impact of climate change-driven extreme weather on rainfall-triggered landslides in Mizoram, NE India"* in the deposited metadata. Its creators are Pritom Sarma and Krishnendu Paul. The malformed `]{` is present in the publisher's title metadata; it is not a TerraSense title correction. The deposit describes an Aizawl-area inventory of 19 rainfall-triggered events from 2016-2025. The raw event workbook `Aizawl_Landslide_Inventory_2015_2025.xlsx` is listed as a downloadable 15,507-byte file, but was not downloaded or inspected. The description claims dates, coordinates, type, trigger, fatalities, and derived rainfall/physics outputs; exact per-row date completeness, clock-time precision, coordinate precision, and verification method are therefore **unverified**. The description identifies some approximate locality centroids, a Cyclone Remal cluster on 2024-05-28, and one retaining-wall failure structurally different from a natural slope failure. Possible overlap with GSI or NASA records has not been measured and cannot be presumed absent.

Zenodo metadata applies CC BY 4.0 to the deposit. That licence generally permits reuse, derivative works, model training, and redistribution with attribution, but the description says the compilation incorporates literature, GSI BhooSanket/Bhukosh, government situation reports, and media reports. The deposit licence does not establish that every upstream record was licensed for those uses. **Effective TerraSense training, derived-model publication, and raw-record redistribution permission remain blocked pending record-level provenance and GSI review.** Obtain author clarification and GSI permission before ingestion. Keep retaining-wall and engineered-structure failures distinguishable from natural landslides. This source is review-only and contributes zero eligible labels at present.

Even if cleared, 19 events are too few and too clustered for temporal model selection, spatial-temporal validation, calibration, or operational claims.

### UGLC 2026

Primary paper and dataset:

- https://essd.copernicus.org/articles/18/4697/2026/
- https://doi.org/10.5281/zenodo.18643456

UGLC contains 1,061,450 validated point records derived from 17 point sources and a separate polygon collection. It standardizes 18 attributes, including source reference, temporal accuracy, spatial accuracy, physical factors, reliability, and notes.

The dataset is CC BY-NC 4.0. Non-commercial research may be possible with attribution, but TerraSense must not assume operational or commercial use. The paper also states that raw inputs are not redistributed because third-party licences differ. UGLC is an integration layer, not an observationally homogeneous label set. Reliability is not validated accuracy, and missing records do not mean no landslide occurred.

No UGLC files were downloaded and no Mizoram count was derived in this audit.

### Global Fatal Landslide Database

Primary publication:

- https://nhess.copernicus.org/articles/18/2161/2018/

The published database covers 4,862 fatal non-seismic landslides from 2004-2016. It records dates, approximate locations, fatalities, injuries, and trigger. The median spatial precision reported in the paper is 681 square kilometres. It is affected by English-language reporting and fatal-event selection. The article's CC BY licence does not establish the underlying database's automation, training, or redistribution terms. No machine-readable current release or Mizoram count was verified.

### DesInventar Sendai

Primary pages:

- https://www.desinventar.net/DesInventar/
- https://www.desinventar.net/download.html

The public database list includes Orissa, Tamil Nadu, and Uttarakhand, but no national India or Mizoram database was found. The DesInventar software licence does not license contributed databases; contributing organisations retain copyright. It cannot supply a Mizoram label set at present.

### Mizoram DMR, SEOC, DDMA, and DIPR

Primary sources:

- State plan: https://dmr.mizoram.gov.in/uploads/attachments/2022/03/353f4dfd194ec41b10171dafa25a1d7e/sdmp-2021-final.pdf
- Aizawl DMR branch: https://aizawl.nic.in/disaster-management-rehabilitation-branch/
- DIPR archive: https://dipr.mizoram.gov.in/category/english-press-releases

The state plan says DMR has landslide records covering 2013-2019. The Aizawl district page requires a damage report to state date, time, and place and says a designated officer performs first-hand verification. This is the strongest prospective gold-label lineage because it can connect occurrence facts, official jurisdiction, evidence, and verification.

No public structured dataset, API, licence, record count, schema, or recurring cadence was found. A direct agreement is required. The future feed should use stable event IDs and preserve the official correction and verification chain.

DIPR provides timestamped official bulletins and can corroborate incidents. Publication time must not be treated as occurrence time. Narrative press releases are incomplete and selection-biased. No scraping or model-use permission was found.

Khuarel appears to be an official state incident/alert application, but no documented public API, data contract, licence, authentication mechanism, or reuse permission was found. It should be approached through DMR rather than reverse engineered.

### NDMA Sachet

Primary integration guide:

- https://sachet.ndma.gov.in/docs/Integration_Guide_For_Agencies.pdf

Sachet documents an ETag-aware CAP XML feed for consuming agencies. It is suitable for official-alert context and future delivery interoperability. A CAP warning is not proof that a landslide occurred. Its issue, effective, and expiry timestamps must not become event occurrence timestamps. A warning can cover a broad area or a hazard that does not materialize.

### IMD

Primary API reference:

- https://api.imd.gov.in/public/api_reference.html

IMD exposes forecasts, observations, warnings, rainfall, nowcast, and other meteorological products. No structured landslide occurrence catalogue was identified. IMD data may become an authoritative dynamic predictor after access, licensing, retention, and redistribution terms are approved. It is never a landslide label by itself.

## Bounded inspection evidence

No bulk event dataset was downloaded. Inspection files were stored only in the system temporary directory. They are outside the repository and project data directories.

| Temporary file | Purpose | Bytes | SHA-256 | Retrieved UTC |
| --- | --- | ---: | --- | --- |
| `zenodo_20783995_metadata.json` | Zenodo metadata only | 16,629 | `205d8f272dbacdb78ca330969e5b782b1b1dfc61eebd2d54e3cdb9f0b7962880` | 2026-09-27T18:35:34.4631689Z |
| `nasa_coolr_portal_item.json` | Events item metadata/licence | 16,129 | `9b96f58cac8b017d74085239dcf2d4602a61c02b60589131546dda4d77d74022` | 2026-09-27T18:36:26.7811409Z |
| `nasa_coolr_layer_schema.json` | Events schema | 16,119 | `81c08332fdd8fae85736ad98af9a5fc2424092098d18ce3a2e4425c208577509` | 2026-09-27T18:37:04.3339274Z |
| `nasa_coolr_mizoram_count.json` | Canonical-polygon count | 11 | `618de7d9f46f3f697d827a1b6d84974760d5deda62e4e592adaa3c646602a94c` | 2026-09-27T18:37:54.0936085Z |
| `nasa_coolr_mizoram_sample10.json` | Empty bounded Events sample | 155 | `10419b994cdb0fb3d630e61052be4ebb660dde3ec8f8d33422367285db4792a3` | Exact retrieval time not captured; file modified 2026-09-27T18:38:03Z |
| `nasa_coolr_reports_item.json` | Reports item metadata/licence | 14,490 | `92fc37c94361ad6b090fd0017fa0a3157f04e697c03e1c752e061ebc6f1cca78` | 2026-09-27T18:39:40.6063113Z |
| `nasa_coolr_reports_schema.json` | Reports schema | 24,013 | `ebac0fac28fc142a3c259c8525564012ad7d073c86e1aa7c48e03571e9dd1c91` | 2026-09-27T18:39:42.4728507Z |
| `nasa_coolr_reports_mizoram_admin_count.json` | Mizoram admin count | 12 | `9fbd205e5992699ce63d88741e36c73c06fb4435ccdbd91b45ba08ce1d875930` | 2026-09-27T18:41:26.7022723Z |
| `nasa_coolr_reports_mizoram_bbox_count.json` | Bounding-box diagnostic | 12 | `9705a251c7441ed4f4ebe50c71d3e81e0d9b09da03ce9985f04c13f92df8ba40` | 2026-09-27T18:41:28.3012320Z |
| `nasa_coolr_reports_mizoram_bbox_sample10.json` | Initial 10-record bounded sample | 14,166 | `d33f048b1ae32c75f91abbe49981cd4fd1a4444e2bf087cb85130ba8de6f3def` | 2026-09-27T18:41:29.2514920Z |
| `nasa_coolr_reports_mizoram_41_bounded.json` | Bounded regional subset for requested statistics | 30,124 | `816c834f0c80f3caed14e03f84d330d3a7cc4d3101090778fec088c3d85434b4` | 2026-09-27T18:48:13.1577343Z |

Every sample is far below the 10 MiB per-source limit. The Zenodo event workbook, UGLC, NRSC inventory, GSI source, and other candidate datasets were not downloaded.

The Zenodo metadata came from `https://zenodo.org/api/records/20783995`. NASA item and schema metadata came from the two linked Earthdata portal items and their `FeatureServer/0` layer metadata. NASA counts and bounded records came from the linked `FeatureServer/0/query` endpoints with `f=json`; counts used `returnCountOnly=true`, while the regional record inspection used only the stated Mizoram filter and `resultRecordCount=100`. The initial ten-record sample used `resultRecordCount=10`. The Events spatial count used the same official endpoint with the current ADM1 Mizoram geometry and `returnCountOnly=true`. The URL paths, filters, response hashes, and boundary hash are sufficient to repeat the inspection without the temporary files; source services may change after the recorded access date.

Four additional temporary diagnostics were retained outside the repository: `nasa_coolr_portal_search.json` (136,865 bytes; SHA-256 `e3fb70daf006a96bdddd13f2e845f1567f9872aa91b1755820603cab25a15345`; Earthdata portal item search, 2026-09-27T18:38:44Z), `nasa_coolr_reports_mizoram_41_bounded.geojson` (104-byte ArcGIS error response; SHA-256 `9f4c25f04f3ca25454d19b91128447a69959de1bb018b0452c575757f2878bfd`), and `nasa_coolr_reports_mizoram_count.json` plus `nasa_coolr_reports_mizoram_sample10.json` (each a 138-byte ArcGIS error response; SHA-256 `ba187a27a880d8ba01eeb6a67da697e6d5a349836fc64c0c945d5fc2a0fd97c5`). These failed responses were excluded from all counts. The valid 41-record JSON response and count-only responses are the evidence used above.

## Canonical event contract

The canonical model must retain two levels:

1. **SourceRecord**: immutable representation of what a provider supplied.
2. **CanonicalEvent**: a reviewed event that links one or more source records without deleting or rewriting them.

A source record can be quarantined, rejected, or superseded. It is never silently removed. A canonical event may merge evidence while retaining every source's wording, date precision, coordinate precision, licence, hash, and lineage.

### Field contract

| Field | Type | Requirement | Source/derivation rule |
| --- | --- | --- | --- |
| `event_id` | UUID | Mandatory for canonical event | Generated after canonical linkage; immutable |
| `source_name` | string | Mandatory on source record | Registry-controlled source identifier |
| `source_record_id` | string | Mandatory | Provider ID; deterministic hash surrogate only when no ID exists |
| `source_url` | URL | Mandatory | Direct record or authoritative source URL |
| `source_licence` | string | Mandatory | Exact reviewed licence ID/status; never guessed |
| `occurred_at` | UTC instant | Nullable | Only when local time, time zone, and precision justify an instant |
| `occurred_date` | ISO date | Nullable | Recorded date; mandatory for temporal-trigger eligibility |
| `time_precision` | enum | Mandatory | Explicit values below |
| `time_zone` | IANA zone/offset | Nullable | Required whenever `occurred_at` is populated |
| `latitude`, `longitude` | WGS84 numbers | Mandatory for spatial eligibility | Original coordinates retained separately |
| `spatial_precision_m` | positive number | Nullable | Provider value or documented derivation, not invented |
| `geometry_source` | enum/string | Mandatory | GPS, field survey, imagery initiation point, locality centroid, geocoded place, provider geometry, unknown |
| `state_code` | code | Derived, nullable | Boundary version and spatial predicate recorded |
| `district_code` | code | Derived, nullable | Boundary version and predicate recorded |
| `zone_id` | code | Derived, nullable | Current prototype zone join; not an official boundary |
| `event_type` | enum | Mandatory | Explicit values below; `UNKNOWN` allowed |
| `severity` | structured nullable | Nullable | Source values plus normalized vocabulary; retain original |
| `fatalities`, `injuries` | non-negative integers | Nullable | Null means unknown, not zero |
| `road_blocked` | boolean | Nullable | Only explicit source or authority verification; null means unknown |
| `verification_status` | enum | Mandatory | Explicit lifecycle below |
| `verification_method` | enum array | Mandatory | Empty only at submission; explicit methods below |
| `confidence` | enum | Mandatory | `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`; evidence rubric, not model probability |
| `reported_at` | UTC instant | Nullable | Report receipt time, never occurrence substitute |
| `verified_at` | UTC instant | Nullable | Populated by verified/rejected authority decision |
| `verified_by` | official account ID | Nullable | Required for authority decisions; no display-name-only identity |
| `retrieved_at` | UTC instant | Mandatory | Adapter retrieval time |
| `raw_record_hash` | SHA-256 | Mandatory | Canonical bytes or documented canonicalization |
| `ingestion_run_id` | UUID | Mandatory | Links immutable retrieval manifest |
| `supersedes_event_id` | UUID | Nullable | Explicit event correction/version lineage |

Additional required source-record fields are `raw_object_uri`, `raw_media_type`, `source_updated_at`, `adapter_version`, `schema_version`, and `licence_snapshot_hash`.

### Time precision

Allowed `time_precision` values:

- `EXACT_INSTANT`: date, clock time, and documented time zone/offset.
- `HOUR`: known hour with documented zone; minutes unknown.
- `PART_OF_DAY`: morning, afternoon, evening, or night.
- `DATE`: calendar date only.
- `DATE_RANGE`: bounded start and end dates.
- `MONTH`: month and year only.
- `YEAR`: year only.
- `UNKNOWN`: no usable occurrence date.

`occurred_at` is populated only for `EXACT_INSTANT` or a separately modelled interval for `HOUR`. `occurred_date` may be populated for date or finer precision. Month/year values must use dedicated interval fields in storage; they must not be encoded as the first day of a month or year.

### Verification status

Allowed values:

- `SUBMITTED`
- `UNDER_REVIEW`
- `VERIFIED`
- `REJECTED`
- `ESCALATED`
- `SUPERSEDED`
- `QUARANTINED`

These values describe evidence review, not model certainty.

### Verification method

Allowed values:

- `OFFICIAL_FIELD_INSPECTION`
- `OFFICIAL_INCIDENT_RECORD`
- `OFFICIAL_RECORD_LINKAGE`
- `REMOTE_SENSING_MANUAL`
- `MULTI_SOURCE_CORROBORATION`
- `SOURCE_ASSERTED`
- `AUTOMATED_DETECTION`
- `UNVERIFIED`

An automated detection cannot be `VERIFIED` solely because an algorithm produced it.

### Confidence

Allowed values:

- `HIGH`: direct official field inspection or equivalent documented evidence with precise location/time.
- `MEDIUM`: corroborated official records with bounded uncertainty.
- `LOW`: credible source with substantial spatial, temporal, or classification uncertainty.
- `UNKNOWN`: no defensible evidence rubric result.

This is categorical evidence confidence, not a calibrated probability.

### Event type

Allowed values:

- `LANDSLIDE_UNSPECIFIED`
- `DEBRIS_FLOW`
- `MUDSLIDE`
- `ROCKFALL`
- `ROCKSLIDE`
- `EARTH_SLIDE`
- `COMPLEX`
- `TOPPLE`
- `SUBSIDENCE`
- `SLOPE_CRACKING`
- `RETAINING_WALL_FAILURE`
- `ROAD_EMBANKMENT_FAILURE`
- `UNKNOWN`

Engineered failures remain distinguishable and are excluded from a natural-landslide label set unless a reviewed modelling objective explicitly includes them.

## Deduplication and canonical linkage

Deduplication is linkage, not deletion.

### Deterministic first-pass keys

1. The tuple `source_name + source_record_id` identifies an immutable source record version.
2. `raw_record_hash` identifies byte-identical retrievals.
3. A source correction creates a new SourceRecord and `supersedes_source_record_id`; it does not overwrite old bytes.
4. Provider-declared parent/child or duplicate relationships are preserved.

### Candidate generation

Candidate pairs are created with transparent rules:

- Same provider ID: deterministic same lineage.
- Same normalized date and distance at or below 250 m when both precision values are at or below 250 m.
- Overlapping occurrence-time intervals and overlapping spatial uncertainty envelopes.
- Same district/locality plus compatible date ranges for coarse records.
- Matching official incident number, source URL lineage, or unique evidence identifier.
- Description similarity may raise a candidate score but never decides identity alone.

For date-only records, the event interval is the local calendar day in the documented jurisdiction time zone. For unknown zones, no instant comparison is allowed. For month/year-only records, candidate generation may use interval overlap, but human review is mandatory.

### Decision policy

Automatic linkage is limited to identical authoritative IDs, explicit source lineage, or byte-identical records. All cross-source event merges require a recorded review decision. The reviewer sees distance, precision envelopes, time overlap, administrative joins, descriptions, source authority, and evidence.

A canonical event keeps:

- all linked source IDs;
- all original geometries and timestamps;
- the canonical geometry with method and uncertainty;
- the canonical time interval with method and precision;
- disagreements;
- the chosen value and reason;
- reviewer identity and timestamp;
- source and licence lineage.

The four same-date/within-10-km COOLR candidate pairs are evidence that loose distance rules would over-merge clustered disasters. No 10-km automatic merge is allowed.

## Label eligibility and gold dataset

### Static susceptibility training

Eligible only when:

- `verification_status=VERIFIED`;
- event type is a natural landslide class included by the model protocol;
- coordinate is valid and `spatial_precision_m` is within the declared terrain-cell sensitivity threshold;
- canonical event is not a duplicate of another label;
- licence permits training and the output's planned use;
- terrain predictors predate or are independent of the event;
- engineered failures, post-event attributes, exposure, and prototype risk fields are excluded.

Occurrence date is not required for a purely static susceptibility presence, but source rights, spatial quality, and verification remain mandatory.

### Temporal-trigger training

Eligible only when all static conditions pass and:

- an occurrence date exists;
- time precision is adequate for the feature window;
- the source time zone is known when subdaily windows are used;
- rainfall, soil moisture, and forecast features are aligned without using observations after failure;
- event location precision is commensurate with predictor resolution;
- observation coverage and missingness are recorded;
- reports from the same storm/event cluster are grouped to prevent fold leakage.

Date-only events may support a daily hazard experiment. They cannot support hourly lead-time claims. Month/year/unknown dates are ineligible.

### Evaluation only

Use for sensitivity or external evaluation when rights permit but precision, source completeness, or verification is weaker than training requirements. Keep results separate from primary validation and label them by source.

### Human review

Required for cross-source duplicate candidates, conflicting dates/locations, structural failures, coarse positions, media-derived reports, missing time zones, and unclear official lineage.

### Exclusion

Exclude rejected, quarantined, fabricated-time, out-of-scope, structurally distinct, licence-blocked, irreconcilably duplicated, or post-event-derived labels. Linked duplicate source records are retained but contribute one canonical event.

### Versioned gold labels

A gold-label release consists of:

- immutable raw-object manifest and hashes;
- source registry version and licence snapshots;
- adapter and schema versions;
- canonical linkage table;
- append-only review decisions;
- eligibility policy version;
- boundary versions and spatial predicates;
- deterministic build command and seed;
- output dataset hash;
- counts by source, precision, status, district, year, and event type;
- excluded-record manifest with machine-readable reasons;
- release notes and superseded release ID.

The dataset is rebuilt from raw objects plus review decisions. Manual spreadsheet edits to the final table are forbidden.

## Automatic ingestion architecture

### Components

1. **Source adapters** retrieve only documented endpoints under approved terms.
2. **Scheduler** emits a source/run idempotency key.
3. **Immutable raw object storage** stores response bytes, headers, retrieval time, ETag/version, licence snapshot, and SHA-256.
4. **Retrieval manifest** records request URL without secrets, adapter version, status, byte count, and parent run.
5. **Schema validator** rejects unexpected fields/types and records schema drift.
6. **Normalizer** converts units, coordinates, enums, and time precision without inventing values.
7. **Quality checks** validate coordinate range, time consistency, uncertainty, source IDs, and administrative joins.
8. **Quarantine** stores invalid or ambiguous records without discarding them.
9. **Candidate linker** generates dedup candidates and deterministic exact-lineage links.
10. **Human review queue** records decisions with role and jurisdiction.
11. **Curated store** publishes versioned SourceRecord and CanonicalEvent tables.
12. **Dataset builder** produces reproducible gold-label releases only from eligible events.
13. **Monitoring** reports last attempt, last success, lag, record counts, schema drift, failures, quarantine volume, and licence expiry/review dates.
14. **Notification** alerts maintainers on repeated failures or staleness; it does not issue public warnings.

### Storage

- Raw payloads: versioned private object storage with retention and legal access controls.
- Retrieval manifests: immutable object plus relational run index.
- Curated events, source records, review, jurisdiction, and audit: transactional PostgreSQL/PostGIS or equivalent.
- Quarantine: separate restricted bucket/table with reason codes.
- Dataset releases: checksummed object storage; public only when every source permits it.
- Secrets: scheduler/workflow secret store; never repository, logs, manifests, client bundles, or URLs.
- Public application: reads approved curated snapshots and freshness metadata, never raw credentials or unreviewed reports.

File/PostGIS abstraction used by the current hierarchy remains unaffected. This architecture is a separate event-data plane.

### Idempotency, retry, and failure

- Run key: `source_id + scheduled_window + adapter_version`.
- Raw-object key: `source_id/retrieval_date/source_record_id/raw_hash`.
- Retry only transient failures with bounded exponential backoff and jitter.
- Respect `Retry-After`, ETag, Last-Modified, provider rate limits, and access windows.
- Do not retry authentication, permission, schema, or licence failures indefinitely.
- Use leases/locks to prevent overlapping runs.
- A repeated payload hash does not create a new source-record version.
- Unexpected schema or content type goes to quarantine.
- Curated publication is atomic: either a fully validated version becomes current or the prior version remains current.
- Last successful update remains visible even when a current run fails.

### Orchestration choices

**GitHub Actions or another CI scheduler** is suitable for low-frequency research checks such as quarterly licence review, annual catalogue version detection, or manually approved historical imports. It is weak for operational feeds because runners are ephemeral, schedule timing is not guaranteed, secrets and artifacts require care, and durable retries/human pauses need external state.

**A durable scheduled worker or workflow service** is appropriate for operational ingestion. It must support persisted steps, queues, leases, retries, idempotency, audit logs, alerting, and pause/resume around human or legal gates. Provider selection is deferred; no paid service is selected here.

**Vercel request handlers alone** are not the ingestion engine. Vercel functions and cron invocations have duration limits, may overlap, and cron delivery must be treated idempotently. They are appropriate for short control-plane calls or status APIs. Long retrieval, validation, backfill, and review workflows belong in durable background infrastructure with object storage and a database.

### Feed cadence and freshness

| Feed | Truthful retrieval cadence | Stale threshold | Notes |
| --- | --- | --- | --- |
| Copernicus GLO-30 | Manual per approved product/version; annual metadata check | New approved version pending review | Static terrain; never hourly |
| Terrain predictors | Rebuild only from approved DEM/version or algorithm change | Manifest mismatch | Offline deterministic artifact |
| GSI historical/incident feed | Only after agreement; daily or weekly if provider supports | 2x agreed interval | No scraping fallback |
| Mizoram DMR/SEOC/DDMA | Event-driven webhook/API plus daily reconciliation if agreed | 15 min for operational event feed, 24 h for reconciliation | Preferred verification source |
| NASA COOLR | Monthly change check until NASA documents a faster cadence | 45 days | Research/discovery; not operational completeness |
| NRSC Atlas | Quarterly landing-page/version check | 18 months | Historical/static mapping |
| UGLC | Annual version check | 18 months | Matches announced yearly review |
| GPM IMERG Early/Late | Each approved half-hourly granule after documented latency; reconcile daily | Two expected granules plus provider latency | Dynamic predictor, not label |
| GPM IMERG Final | Monthly/versioned reconciliation after provider release | Product-specific | Retrospective training/evaluation |
| SMAP soil moisture | Per approved daily product release | 2 days plus provider latency | Dynamic predictor |
| ECMWF or approved forecast | Each available model cycle, typically 6-hourly where licensed | One missed cycle plus latency | Retain issue time and model version |
| IMD weather/warnings | Per approved API cadence | Product-specific | Official weather context |
| Public field reports | Event-driven | Queue age SLA | Unverified until authority decision |
| Authority verification | Event-driven plus daily backlog monitor | Jurisdiction SLA | Append-only decisions |
| NDMA CAP alerts | ETag polling at agency-approved interval | 2x interval | Alerts are not occurrence labels |
| Delivery receipts | Webhook/event-driven; bounded polling fallback | Channel SLA | Channel-neutral alert linkage |

Cadence must follow provider documentation and agreements. Faster polling does not create fresher truth.

## Model implications

### Static susceptibility

Static susceptibility uses terrain and other slowly changing environmental predictors to rank where landslides are more likely relative to other locations. It remains the Phase 5A/5B terrain-only experimental path. It does not require occurrence time for every spatial presence, but it still requires licensed, verified, spatially suitable labels and spatial validation.

### Dynamic trigger forecasting

Dynamic trigger modelling needs timestamped occurrences and time-aligned hydro-meteorological windows. It asks when current or forecast conditions raise risk at susceptible locations. It requires event dates, known time semantics, non-event observation windows, source completeness, and strictly causal feature cutoffs.

Any future comparison windows without recorded events are sampled background time windows, not confirmed landslide-free observations. Their construction must account for uneven reporting effort and must be declared before validation.

No dynamic model may be trained from the current data.

### Model family order

1. **Logistic regression baseline.** Use declared lag/window summaries, regularization, and interpretable coefficients.
2. **Discrete-time hazard baseline.** Prefer when the unit is location-time and censoring/non-event windows are explicit.
3. **Tree-based baseline.** Use a constrained random forest or gradient-boosted trees after the linear/hazard baseline.
4. **XGBoost or LightGBM.** Appropriate for nonlinear interactions among engineered lag/window features when sample size and validation justify it. XGBoost does not natively model raw sequences, event dependence, censoring, or storm clusters.
5. **Temporal convolution or GRU/LSTM.** Consider only after a much larger, regularly sampled, well-aligned event/time-window dataset exists and simpler baselines are decisively outperformed.
6. **Temporal Fusion Transformer or similar attention model.** Requires substantially more events, seasons, covariates, careful leakage controls, and compute. It is not justified by the current evidence.
7. **Spatiotemporal point process.** Scientifically relevant if catalogue completeness, timing, and spatial uncertainty support occurrence intensity modelling. Current reporting bias and unknown non-event observation effort block it.

### Minimum entry evidence

These are conservative experiment-entry gates, not guarantees of scientific power:

| Stage | Minimum evidence |
| --- | --- |
| Daily logistic/XGBoost or discrete hazard experiment | At least 200 verified natural landslide events with date precision; at least 5 distinct monsoon seasons; at least 3 districts; documented observation/non-event windows; usable predictor coverage; enough events for at least 5 spatial-temporal outer folds with roughly 30 events per evaluable fold |
| Subdaily trigger experiment | At least 500 verified events with documented clock time and time zone; at least 5-8 monsoon seasons; subdaily rainfall/soil coverage and explicit reporting effort |
| TCN or GRU/LSTM comparison | At least 2,000 high-quality event sequences across 8-10 seasons and geographically separated validation; effective sample size reassessed after storm clustering |
| TFT/attention model | At least 5,000 high-quality sequences, stable covariate availability, multiple districts/seasons, and a predeclared compute and ablation plan |
| Spatiotemporal point process | At least 1,000 precisely timed and located events plus defensible catalogue completeness/observation-effort model |

A power and effective-sample-size analysis may raise every threshold. Event clusters from one storm cannot be counted as independent seasons.

### Validation requirements

- Outer evaluation separates both geography and time, such as held-out districts plus held-out monsoon seasons.
- All records from one storm cluster and duplicate-linked canonical event stay in one fold.
- Lag and window features stop before the declared prediction cutoff.
- Predictor availability is reconstructed as it was known at forecast issue time.
- Hyperparameters are selected only inside training folds.
- PR-AUC is primary for rare events; ROC-AUC is secondary.
- Report recall, precision, balanced accuracy, confusion matrices, Brier score, reliability diagrams, lead-time performance, and per-fold variability.
- Calibration is assessed only on held-out spatial-temporal data.
- Probability terminology remains forbidden without adequate held-out calibration.
- Compare against climatology, seasonal rate, static susceptibility, persistence, and simple rainfall thresholds.
- Report uncertainty across folds, sources, coordinate precision, and event-time precision.

## Authority Operations Portal contracts

The Authority Operations Portal is a future separate application surface. It is not a role toggle on the public dashboard. No UI, authentication, account, or notification integration is implemented in this phase.

### Identity and jurisdiction

- Accounts are provisioned by an authorized administrator.
- There is no unrestricted public officer signup.
- Every active assignment has role, state, district, optional zone/geofence, start, end, approver, and reason.
- Account lifecycle supports invited, active, suspended, revoked, and expired.
- Suspension/revocation invalidates sessions and blocks new decisions.
- Password reset requires verified organizational identity.
- Sessions have idle and absolute expiry, rotation, revocation, secure cookies/tokens, and device/audit metadata.
- MFA is required for alert approvers and system administrators and recommended for all officials.
- Authorization is enforced server-side for every object and transition.
- Least privilege and jurisdiction intersection apply: a district officer cannot approve another district's event or alert.
- Break-glass access requires a reason, short expiry, independent review, and immutable audit entry.
- Read-only auditors cannot mutate records.

### Roles

| Role | Core permissions | Prohibited actions |
| --- | --- | --- |
| Field verifier | View assigned reports; add evidence; recommend verification within jurisdiction | Approve public alerts; manage users; alter audit history |
| District officer | Decide reports and draft/submit district alerts | Approve state-wide alerts outside jurisdiction; self-approve high-severity alert |
| State officer | Review escalations; curate statewide incidents; draft statewide alerts | Administer system secrets; erase evidence |
| Alert approver | Approve/reject alerts within assigned jurisdiction | Prepare and approve the same high-severity alert |
| System administrator | Provision accounts, roles, integrations, and policy configuration | Alter scientific evidence or approve warnings by default |
| Read-only auditor | Read records, versions, decisions, receipts, and logs | Any mutation |

### Field report contract and lifecycle

`SUBMITTED -> UNDER_REVIEW -> VERIFIED or REJECTED -> optionally ESCALATED`

Every transition records:

- transition ID and idempotency key;
- report and version ID;
- acting official account;
- active role and jurisdiction;
- UTC timestamp;
- previous and new status;
- reason code and free-text rationale;
- evidence object IDs and hashes;
- location/time corrections with before/after values;
- policy version;
- immutable audit entry hash and previous-entry hash.

A public report enters as `SUBMITTED` and `UNVERIFIED`. It never becomes a training label on submission. Verification requires evidence appropriate to the policy, spatial and temporal precision, event classification, source rights, and a jurisdiction-authorized official. Rejection does not delete the report. Escalation preserves the prior decision and reason.

### Alert contract and lifecycle

`DRAFT -> PENDING_APPROVAL -> APPROVED -> SCHEDULED or SENT -> DELIVERY_TRACKED -> EXPIRED or CANCELLED`

A channel-neutral alert contains:

- alert ID and version;
- jurisdiction/geofence and boundary version;
- severity, urgency, certainty, issue/effective/expiry times;
- multilingual title, body, recommended action, and correction text;
- source and evidence links;
- model/version, score semantics, calibration status, and freshness snapshot;
- preparer, approver(s), and decision reasons;
- idempotency key;
- correction/cancellation lineage;
- per-channel delivery intent and receipt summary.

The model may recommend an alert. It never sends one.

High-severity alerts require two-person control:

1. one authorized official prepares and submits;
2. a different authorized official approves.

The service rejects self-approval, expired evidence, out-of-jurisdiction approval, stale data beyond policy, duplicate sends, and missing correction lineage. Emergency cancellation is separately authorized and immediately propagated to delivery adapters.

Targets can be a state, district, zone, approved boundary version, or explicit geofence. Prototype Aizawl zones must be labelled as prototype analysis zones, not official administrative warning units.

### Delivery adapters

Potential adapters include in-app notifications, web push, SMS, email, WhatsApp through an approved provider, and future government broadcast integrations. None is claimed as available now.

Each adapter implements:

- provider authorization and secret isolation;
- per-channel message rendering;
- idempotency and duplicate-send suppression;
- bounded retries and provider rate limits;
- delivery, failure, bounce, and opt-out receipts;
- correction and cancellation support;
- provider message ID and timestamp;
- lawful recipient/consent policy.

The existing demo SMS provider and `/alerts/test` route are not an official delivery mechanism.

### Audit and safety

- Append-only audit events and alert versions.
- Tamper-evident hash chain or equivalent immutable storage.
- Delivery receipts retained where providers supply them.
- Rate limits by official, jurisdiction, alert, recipient, and channel.
- Duplicate-send protection across retries and adapters.
- Emergency cancellation and correction workflows.
- Model version, score type, calibration status, source timestamps, last successful feed updates, missing feeds, and staleness shown to the approving official.
- Clear labels separating prototype recommendations from official warnings.
- No silent fallback from unavailable data to a fabricated current value.
- No model output may override an authority decision.

## Existing repository contract gaps

The current `backend/routes/field_reports.py` model stores reports in an in-memory dictionary. Its fields support a basic timestamp, coordinates, zone, category, severity, description, reporter, and sync status. It has no authenticated official, jurisdiction, durable evidence, verification lifecycle, source licence, event-time precision, immutable audit, deduplication, or training-eligibility contract.

The current `backend/routes/alerts.py` stores a prototype alert list in memory. The SMS service defaults to a demo provider; real Twilio integration is explicitly not configured. There is no approval workflow, two-person rule, geofenced targeting, versioning, cancellation, delivery receipt persistence, or official identity.

The current exposure routes summarize mapped cached OSM roads, settlements, and facilities. They are exposure/access context and must stay outside event labels.

No existing runtime route changes in Phase 5B-2.

## Exact next-phase entry criteria

A data-ingestion implementation may begin only after all applicable gates are met:

1. Written GSI decision on training, transformation, raw storage, redistribution, recurring retrieval, commercial/operational use, and derived model/output publication.
2. Written Mizoram DMR/SEOC/DDMA data-sharing agreement with named data controller and security/privacy terms.
3. Approved source-specific licence snapshots and attribution text.
4. Documented API/export endpoints, authentication, rate limits, cadence, retention, correction, and deprecation policy.
5. Stable source IDs and a test dataset containing date/time precision, time zone, coordinates, spatial uncertainty, event type, evidence, and verification lineage.
6. Confirmed ability to retain immutable raw responses and hashes.
7. Approved handling of personal information and sensitive incident evidence.
8. Canonical schema and controlled vocabularies reviewed by disaster-management and geotechnical domain owners.
9. Deduplication thresholds and review protocol approved before any merge decisions.
10. At least one deterministic source adapter tested against a provider-approved sandbox or fixture.
11. Gold-label release process reproduces identical hashes from raw manifests and decisions.
12. At least 200 eligible date-level natural events over five monsoon seasons and three districts before daily temporal baseline training.
13. A documented observation/non-event-window policy and spatial-temporal validation protocol.
14. An explicit decision on research-only versus operational/commercial scope for every source.
15. Security review for authority identity, jurisdiction, audit, and secrets before any portal implementation.

### Recommended official actions

- Send a formal GSI permission request using the terms/contact addresses.
- Ask Mizoram DMR/SEOC for a structured, versioned export or feed and nominate a data steward.
- Ask Aizawl and other DDMAs for the data dictionary, verification form, historical digitization coverage, and correction procedure.
- Ask NRSC for dataset-specific permission and a lawful machine-readable delivery route for the Mizoram inventory.
- Ask NASA Earthdata GIS to confirm recurring FeatureServer retrieval terms, rate limits, citation requirements, and change semantics.
- Ask the Aizawl Zenodo authors for record-level provenance, coordinate derivation, time-zone semantics, and confirmation of upstream permissions.
- Ask IMD for approved API access, training/retention/redistribution rights, and historical product/version access.
- Ask NDMA about authorized CAP consumption, retention, display, and downstream-delivery integration.

## Scope confirmation

This phase did not:

- train or evaluate a model;
- build terrain predictors;
- access raster bodies;
- transform or use GSI records;
- create labels or background samples;
- create authentication or authority UI;
- change APIs, backend, frontend, dependencies, deployment, PostGIS, or risk scoring;
- download any bulk event dataset;
- infer any occurrence date or timestamp;
- stage, commit, push, deploy, or open a pull request.

The present prototype scorer remains unchanged and must continue to be described as a heuristic relative prototype score.
