# data/sample/ — Sample / Mock Data

> ⛔ **FOR UI AND API TESTING ONLY**
>
> All datasets in this directory are **fabricated sample data**.
> They are used exclusively to render the dashboard and test API contracts
> during development phases before real data sources are connected.
>
> **These files must never be used to train or evaluate ML models.**
> **No values in these files represent real sensor readings, satellite observations, or validated measurements.**

---

## Files

| File | Purpose |
|------|---------|
| `grid-risk.geojson` | 5×5 mock risk grid over approximate Aizawl bounds |
| `roads.geojson` | Fictitious road segments for UI rendering |
| `villages.geojson` | Fictitious village locations |
| `hospitals.geojson` | Fictitious critical facility locations |

---

## Common fields

All features include `"data_type": "SAMPLE_MOCK"` in their properties.
The FeatureCollection root includes `"data_type": "SAMPLE_MOCK"` and a `"disclaimer"` field.

---

## Coordinate system

WGS84 (EPSG:4326). Grid is centered approximately on Aizawl city (23.7271°N, 92.7176°E) but the individual zone values are **not derived from real terrain data**. Phase 5 replaces this grid with real SRTM-derived terrain features.

---

## Frontend public copies

The `frontend/public/data/sample/` directory contains identical copies of these files served as static assets for the browser. If you update these canonical files, copy the changes there too.
