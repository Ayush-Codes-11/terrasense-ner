# TerraSense NER

**AI-powered landslide early warning and monitoring platform — North Eastern Region, India**

> ⚠️ **Prototype Disclaimer:** This is a demonstration prototype. All risk scores, emergency priorities, and forecasts are produced by a prototype scoring engine and are **not validated** against real landslide occurrence data. Outputs must not be used for operational disaster response decisions.

---

## Pilot Area & Designed Coverage

**Current prototype coverage:** Aizawl District, Mizoram — chosen for its landslide relevance, available terrain data, and manageable geographic scope.
**Intended deployment coverage:** all North Eastern states

### Scaling Architecture
TerraSense is architected to scale geographically:
1. **Pilot** → Aizawl pilot validates the full pipeline.
2. **District** → Extend ingestion and processing district-by-district using tiled DEM, rainfall feeds and spatial databases.
3. **State** → State-scale tiled processing.
4. **NER Scale** → NER-wide command dashboard with on-demand state/district risk layers and unified alerting.

*Note: The frontend currently provides three basemap toggle options (Terrain via OpenTopoMap, Streets, and Satellite) for testing and demonstration. A future production implementation can use Google Maps, ArcGIS, Mapbox or another approved mapping provider while preserving the same TerraSense GIS overlays and backend.*

---

## Repository Structure

```
terrasense-ner/
├── frontend/          # React + Vite + TypeScript + Tailwind + React-Leaflet
├── backend/           # Python + FastAPI (no ML imports)
├── ml/                # Prototype risk scorer; optional XGBoost upgrade
├── data/
│   ├── sample/        # Mock data for UI/API testing ONLY — never used for ML training
│   └── real/          # Real OSM exports, SRTM terrain, weather API responses
├── notebooks/         # Exploration notebooks (not production code)
└── README.md
```

---

## Data Lineage

| Directory | Purpose | Provenance |
|-----------|---------|------------|
| `data/sample/` | UI rendering and API contract tests | MOCK / SYNTHETIC |
| `data/real/osm/` | Roads, communities, facilities | REAL OpenStreetMap |
| `data/real/terrain/` | Slope/elevation | REAL Copernicus GLO-30 DEM |
| `data/real/weather/` | Recent rainfall inputs | NASA GPM IMERG (Integration status: adapter implemented. Current runtime: SAMPLE / offline fixture. Real operational ingestion requires Earthdata-authenticated fetch) |
| `data/real/gsi/` | Landslide inventory | REAL GSI public inventory |

**Map layers & UI representation:**
* **Roads / Critical facilities / Communities:** Displayed using real OpenStreetMap data where available.
* **Risk Zones:** 25 georeferenced prototype analysis boundaries (5×5 grid over Aizawl), not official administrative or hazard boundaries.

---

## Quickstart

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Backend (Phase 3+)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000
```

> **Python Runtime:** Python 3.12 selected for stable Vercel support and broad pre-built binary-wheel compatibility for NumPy, Shapely and PyProj (`backend/.python-version`).

### ML (Phase 4+)
```bash
cd ml
pip install -r requirements.txt
python prototype_scorer.py
```

### Mandatory Pre-Push Gate & Git Hooks (Deployment Bundle Parity)
To prevent canonical `data/` and `ml/` from diverging from `backend/data/` and `backend/ml/`:

1. **Activate Local Git Hooks (One-time per clone):**
   `core.hooksPath` is a local Git configuration and is not enabled automatically simply because `.githooks/` is committed. Run:
   ```bash
   git config core.hooksPath .githooks
   ```
   - **`.githooks/pre-commit`**: Automatically runs `python backend/scripts/sync_deployment_bundle.py`, stages any updated `backend/data` and `backend/ml` files into the same commit, and verifies parity before the commit is created.
   - **`.githooks/pre-push`**: Non-mutating verification gate that ensures parity is 100% satisfied before push.

2. **Mandatory Step for Antigravity & Developers:**
   Every future TerraSense coding phase must finish with:
   ```bash
   python backend/scripts/sync_deployment_bundle.py
   python -m pytest backend/tests/test_deployment_sync.py
   ```
   before commit/push.

3. **CI Semantics:**
   GitHub Actions CI (`.github/workflows/ci.yml`) provides repository-level parity and regression detection after push. Note: Because Vercel Git auto-deployments trigger independently upon Git push, CI failure detects regressions on GitHub after push, but does not intercept Vercel deployment unless custom Vercel Deployment Checks or deployment pipelines are configured.

---

## Build Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ | Repo structure + React frontend shell |
| 2 | ✅ | Leaflet GIS map + sample GeoJSON |
| 3 | ✅ | FastAPI backend (sample data) |
| 4 | ✅ | Prototype risk scorer + antecedent rainfall |
| 5 | ✅ | Rainfall-triggered 24/48/72h landslide-risk outlook |
| 6 | ✅ | Real OSM exposure engine + decision-support priority |
| 7 | ✅ | Real DEM terrain (Copernicus GLO-30) + GSI Landslide Inventory |
| Deployment | ✅ | Vercel Git auto-deployment configuration & Parity CI |
| 8 | ✅ | Real NASA GPM precipitation integration |
| 9 | ✅ | Field reporting & community validation |
| 10 | ✅ | PWA + offline capability |
| 11 | ✅ | Prototype Alert Engine (PWA/SMS demo) |
| 12 | ✅ | Map Visual Upgrade, UI Polish + SIH Production Handoff |

---

## Key Design Decisions

- **Sample-first:** every feature works with mock data before any real API is wired
- **No fabrication:** accuracy metrics, SHAP values, and rainfall figures are never invented
- **Antecedent rainfall:** forecast windows accumulate prior observed rainfall before scoring
- **Road exposure ≠ road blocked:** a road is only marked blocked on a verified field report
- **Priority label:** always shown as "Prototype Decision-Support Priority — not official"
- **Continuous terrain derivatives:** Horn 3×3 slope/aspect calculated across continuous projected DEM before zonal masking

## Storage & Persistence Limits (Prototype)
- **Field Report Offline Cache**: Persistent on the user's browser/device via IndexedDB.
- **Backend Field-Report Collection**: Prototype/demo acknowledgement storage. Non-persistent across serverless restarts.
- **Alert History Backend**: Prototype in-memory history. Non-persistent across serverless restarts.
- *(Future real production architecture will utilize a PostgreSQL/PostGIS / Supabase or equivalent persistent datastore, but this is not active in the current prototype).*

