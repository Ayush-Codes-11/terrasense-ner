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
from routes.hierarchy import router as hierarchy_router

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

import os

# Allowed production and local origins
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
if os.getenv("FRONTEND_URL"):
    _CORS_ORIGINS.append(os.getenv("FRONTEND_URL").rstrip("/"))

# CORS Configuration:
# - Localhost development (ports 5173, 5174)
# - Production frontend via FRONTEND_URL environment variable
# - Vercel Preview deployments matching terrasense-*.vercel.app
# - Credentials false (no cookies/session tokens in current phase)
# - Methods strictly GET (Note: Phase 8 field report submissions will require adding "POST")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"^https://terrasense-.*\.vercel\.app$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

from routes.field_reports import router as field_reports_router
from routes.alerts import router as alerts_router

app.include_router(zones_router)         # /health, /zones
app.include_router(risk_router)          # /risk/current, /risk/forecast/{id}
app.include_router(weather_router)       # /weather/{id}
app.include_router(geodata_router)       # /geodata/osm/*
app.include_router(exposure_router)      # /exposure/{id}
app.include_router(priority_router)      # /priority/{id}
app.include_router(terrain_router)       # /terrain/status, /terrain/{zone_id}
app.include_router(hierarchy_router)     # /hierarchy/region, /hierarchy/states, /hierarchy/districts
app.include_router(field_reports_router) # /field-reports
app.include_router(alerts_router)        # /alerts



# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "TerraSense NER API",
        "phase": "real_data_ingestion_complete",
        "docs": "/docs",
        "health": "/health",
        "data_mode": "PER_SOURCE_PROVENANCE",
        "disclaimer": (
            "All data is fabricated for UI/API testing. "
            "Not for operational disaster-management use."
        ),
    }
