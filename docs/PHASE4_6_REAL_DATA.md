# Phases 4–6 real-data slice

This branch adds a reviewable foundation for GIS evidence, static
susceptibility preparation, and dynamic fusion.

## Phase 4: GIS evidence

`GET /risk/real/{zone_id}` combines the existing pilot-zone outputs from:

- Copernicus DEM GLO-30 zonal terrain statistics
- NASA GPM IMERG observed rainfall
- NASA SMAP root-zone wetness
- ECMWF/Open-Meteo forecast snapshot
- GSI BhooSanket Mizoram landslide inventory

The response includes source provenance for each component. The existing
`/terrain` endpoints remain unchanged.

## Phase 5: static susceptibility

`backend/scripts/build_static_susceptibility_dataset.py` creates
`data/real/landslides/static_susceptibility_dataset.json` by spatially joining
the real GSI points to the existing Aizawl pilot grid and attaching real DEM
features.

This is a feature table, not a trained XGBoost model. The public GSI layer has
no usable event dates, so it cannot support a temporally linked rainfall
trigger model or calibrated probability. No model or accuracy claim is
included.

## Phase 6: dynamic fusion

`GET /risk/real/{zone_id}` returns bounded static, trigger, and combined
indices. These are transparent relative decision-support indices, not
probabilities and not calibrated alerts. `/risk/real/status` exposes the
model-readiness and data-provenance state.

The implementation intentionally fails closed for unknown zones and reports
missing real inputs instead of silently substituting fabricated values.
