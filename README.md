# TerraSense NER

**AI-powered landslide early warning and monitoring platform — North Eastern Region, India**

> ⚠️ **Prototype Disclaimer:** This is a demonstration prototype. All risk scores, emergency priorities, and forecasts are produced by a prototype scoring engine and are **not validated** against real landslide occurrence data. Outputs must not be used for operational disaster response decisions.

---

## Pilot Area

**Aizawl District, Mizoram** — chosen for its landslide relevance, available terrain data, and manageable geographic scope.

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

| Directory | Purpose | ML training? |
|-----------|---------|-------------|
| `data/sample/` | UI rendering and API contract tests | ❌ Never |
| `data/real/osm/` | OSM roads, villages, hospitals | N/A (geodata) |
| `data/real/terrain/` | Slope/elevation from SRTM DEM | ✅ If labelled |
| `data/real/weather/` | Real weather API responses | Input only |

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

### Mandatory Pre-Push Gate (Deployment Bundle Parity)
Every future TerraSense coding phase and developer commit must finish with:
```bash
python backend/scripts/sync_deployment_bundle.py
python -m pytest backend/tests/test_deployment_sync.py
```
before commit/push. This synchronizes canonical `data/` and `ml/` into `backend/data/` and `backend/ml/` and asserts 100% SHA-256 parity in CI.

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
| 8 | ⏳ | Field reporting & community validation |
| 9 | ⏳ | PWA + offline capability |
| 10 | ⏳ | Alerts + charts |
| 11 | ⏳ | Polish + production handoff |

---

## Key Design Decisions

- **Sample-first:** every feature works with mock data before any real API is wired
- **No fabrication:** accuracy metrics, SHAP values, and rainfall figures are never invented
- **Antecedent rainfall:** forecast windows accumulate prior observed rainfall before scoring
- **Road exposure ≠ road blocked:** a road is only marked blocked on a verified field report
- **Priority label:** always shown as "Prototype Decision-Support Priority — not official"
- **Continuous terrain derivatives:** Horn 3×3 slope/aspect calculated across continuous projected DEM before zonal masking

