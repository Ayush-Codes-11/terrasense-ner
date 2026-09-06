"""
TerraSense NER — FastAPI backend
Phase 3: sample-data API layer (no ML, no real data sources)

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000

Or from the repo root:
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.zones import router as zones_router
from routes.risk import router as risk_router
from routes.weather import router as weather_router
from routes.geodata import router as geodata_router
from routes.exposure import router as exposure_router
from routes.priority import router as priority_router
from routes.terrain import router as terrain_router

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TerraSense NER API",
    description=(
        "AI-powered landslide early-warning API for Aizawl pilot district. "
        "**Phase 3**: all endpoints serve SAMPLE_MOCK data from data/sample/. "
        "No real sensor data, ML models, or calibrated predictions are active."
    ),
    version="0.1.0-phase3",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "TerraSense NER Team",
        "url": "https://github.com/Ayush-Codes-11/terrasense-ner",
    },
    license_info={"name": "MIT"},
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Allow the Vite dev server and any production frontend origin.
# Tighten this in production.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["GET"],   # Phase 3 is read-only
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(zones_router)         # /health, /zones
app.include_router(risk_router)          # /risk/current, /risk/forecast/{id}
app.include_router(weather_router)       # /weather/{id}
app.include_router(geodata_router)       # /geodata/osm/*
app.include_router(exposure_router)      # /exposure/{id}
app.include_router(priority_router)      # /priority/{id}
app.include_router(terrain_router)       # /terrain/status, /terrain/{zone_id}



# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "TerraSense NER API",
        "phase": "3 — Sample data layer",
        "docs": "/docs",
        "health": "/health",
        "data_mode": "SAMPLE_MOCK",
        "disclaimer": (
            "All data is fabricated for UI/API testing. "
            "Not for operational disaster-management use."
        ),
    }
