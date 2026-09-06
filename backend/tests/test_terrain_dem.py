"""
test_terrain_dem.py — Tests for Phase 7 REAL_DEM terrain integration.

Covers:
1.  DEM metadata file loads and is well-formed.
2.  Zonal terrain JSON loads with correct structure.
3.  CRS is EPSG:4326 for the raw DEM tile.
4.  Processing CRS is EPSG:32646 (UTM Zone 46N — metric).
5.  Zonal stats: all 25 zones are present.
6.  C03 specific terrain values (regression guard).
7.  Slope is derived from Horn gradient in metric CRS (>0, <90).
8.  Circular mean aspect is in [0, 360).
9.  No-data fraction is a fraction [0.0, 1.0].
10. risk_engine uses REAL_DEM slope for C03 (not SAMPLE_MOCK 42°).
11. GET /terrain/status returns REAL_DEM status.
12. GET /terrain/C03 returns correct zone data.
13. GET /terrain/INVALID returns 404.
14. feature_provenance in /risk/current/C03 shows REAL_DEM slope.
15. feature_provenance in /risk/forecast/C03 shows REAL_DEM slope.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

_TERRAIN_DIR = _REPO_ROOT / "data" / "real" / "terrain"
_META_FILE = _TERRAIN_DIR / "metadata.json"
_ZONAL_FILE = _TERRAIN_DIR / "zonal_terrain.json"

# Skip the whole module if DEM files are not present
pytestmark = pytest.mark.skipif(
    not _META_FILE.exists() or not _ZONAL_FILE.exists(),
    reason="Terrain DEM files not present — run backend/scripts/fetch_or_prepare_dem.py first",
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def meta():
    with open(_META_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def zonal():
    with open(_ZONAL_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def zones(zonal):
    return zonal.get("zones", {})


@pytest.fixture(scope="module")
def c03(zones):
    return zones.get("C03")


# ─── 1. Metadata file structure ──────────────────────────────────────────────

def test_meta_loads(meta):
    """Metadata file loads and has required keys."""
    required_keys = {"source", "product", "crs", "spatial_resolution", "retrieved_at",
                     "tile_name", "dimensions", "file_size_bytes", "nodata_value",
                     "nodata_percentage", "attribution"}
    for key in required_keys:
        assert key in meta, f"Missing key in metadata.json: {key}"


# ─── 2. Zonal terrain JSON structure ─────────────────────────────────────────

def test_zonal_loads(zonal):
    """Zonal terrain JSON loads and has dataset metadata."""
    assert "zones" in zonal
    assert "total_zones" in zonal
    assert "processing_crs" in zonal


# ─── 3. Raw DEM CRS is geographic ────────────────────────────────────────────

def test_meta_crs_geographic(meta):
    """Raw DEM tile is in EPSG:4326 (geographic)."""
    assert meta["crs"] == "EPSG:4326", f"Expected EPSG:4326, got {meta['crs']}"


# ─── 4. Processing CRS is metric UTM 46N ─────────────────────────────────────

def test_processing_crs_metric(zonal):
    """Zonal processing CRS is EPSG:32646 (UTM Zone 46N — metric)."""
    assert "32646" in zonal.get("processing_crs", ""), (
        f"Expected EPSG:32646 in processing_crs, got: {zonal.get('processing_crs')}"
    )


# ─── 5. All 25 zones present ─────────────────────────────────────────────────

def test_all_25_zones_present(zones):
    """All 25 pilot zones A01–E05 are in zonal_terrain.json."""
    expected = [f"{r}{c:02d}" for r in "ABCDE" for c in range(1, 6)]
    missing = [z for z in expected if z not in zones]
    assert not missing, f"Missing zones: {missing}"


# ─── 6. C03 regression values ────────────────────────────────────────────────

def test_c03_terrain_values(c03):
    """C03 terrain stats match known Copernicus GLO-30 computed values."""
    assert c03 is not None, "C03 not found in zonal_terrain.json"
    # Exact regression values from the processor run
    assert abs(c03["mean_elevation_m"] - 980.8) < 1.0, f"C03 elevation mismatch: {c03['mean_elevation_m']}"
    assert abs(c03["mean_slope_deg"] - 22.06) < 0.5, f"C03 slope mismatch: {c03['mean_slope_deg']}"
    assert abs(c03["circular_mean_aspect_deg"] - 117.4) < 2.0, f"C03 aspect mismatch: {c03['circular_mean_aspect_deg']}"
    assert c03["valid_pixel_count"] > 0


# ─── 7. Slope plausibility ────────────────────────────────────────────────────

def test_slope_plausible(zones):
    """All zone mean slopes are in (0°, 90°) — impossible if computed incorrectly."""
    for zone_id, z in zones.items():
        s = z["mean_slope_deg"]
        assert 0 < s < 90, f"Zone {zone_id}: implausible slope {s}°"


# ─── 8. Circular mean aspect in [0, 360) ─────────────────────────────────────

def test_aspect_in_range(zones):
    """All zone circular mean aspects are in [0°, 360°)."""
    for zone_id, z in zones.items():
        a = z["circular_mean_aspect_deg"]
        assert 0.0 <= a < 360.0, f"Zone {zone_id}: aspect {a}° out of range"


# ─── 9. Nodata fraction [0, 1] ───────────────────────────────────────────────

def test_nodata_fraction(zones):
    """Nodata fraction is a valid fraction [0.0, 1.0] for all zones."""
    for zone_id, z in zones.items():
        nd = z["nodata_fraction"]
        assert 0.0 <= nd <= 1.0, f"Zone {zone_id}: nodata_fraction {nd} out of range"


# ─── 10. Risk engine uses REAL_DEM slope for C03 ─────────────────────────────

def test_risk_engine_uses_real_slope():
    """Risk engine must use REAL_DEM slope (22.06°) not SAMPLE_MOCK slope (42°) for C03."""
    from backend.services.risk_engine import compute_zone_risk

    # Provide zone_props with old SAMPLE_MOCK slope — engine should override with REAL_DEM
    props = {
        "zone_id": "C03",
        "slope": 42.0,          # old SAMPLE_MOCK value
        "elevation": 1520.0,    # old SAMPLE_MOCK value
        "rain_24h": 45.0,
        "rain_3d": 80.0,
        "soil_wetness_index": 0.5,
    }
    result = compute_zone_risk(props)

    prov = getattr(result, "feature_provenance", {})
    used_slope = getattr(result, "used_slope_deg", None)

    assert prov.get("slope") == "REAL_DEM", f"Expected slope=REAL_DEM, got: {prov}"
    assert prov.get("elevation") == "REAL_DEM", f"Expected elevation=REAL_DEM, got: {prov}"
    assert prov.get("rainfall") == "SAMPLE_MOCK"
    assert prov.get("soil_wetness") == "SAMPLE_MOCK"

    # REAL_DEM slope for C03 is ~22.06°, not 42°
    if used_slope is not None:
        assert abs(used_slope - 22.06) < 1.0, (
            f"Engine used slope {used_slope}° — expected ~22.06° (REAL_DEM), not 42° (SAMPLE_MOCK)"
        )


# ─── 11–13. Terrain API endpoints ────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_client():
    from fastapi.testclient import TestClient
    # Import from backend directory
    old_path = sys.path[:]
    sys.path.insert(0, str(_REPO_ROOT / "backend"))
    try:
        import main
        return TestClient(main.app)
    finally:
        sys.path[:] = old_path


def test_terrain_status_endpoint(test_client):
    """GET /terrain/status returns REAL_DEM status with required fields."""
    resp = test_client.get("/terrain/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REAL_DEM"
    assert data["is_real"] is True
    assert "Copernicus" in data.get("source", "")
    assert data.get("total_zones_with_terrain", 0) > 0


def test_terrain_c03_endpoint(test_client):
    """GET /terrain/C03 returns correct zonal stats."""
    resp = test_client.get("/terrain/C03")
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone_id"] == "C03"
    assert "mean_slope_deg" in data
    assert "mean_elevation_m" in data
    assert "circular_mean_aspect_deg" in data
    assert abs(data["mean_slope_deg"] - 22.06) < 1.0


def test_terrain_invalid_zone_returns_404(test_client):
    """GET /terrain/INVALID returns 404."""
    resp = test_client.get("/terrain/INVALID")
    assert resp.status_code == 404


# ─── 14. /risk/current/C03 has feature_provenance ────────────────────────────

def test_risk_current_c03_has_provenance(test_client):
    """GET /risk/current/C03 exposes feature_provenance with REAL_DEM slope."""
    resp = test_client.get("/risk/current/C03")
    assert resp.status_code == 200
    data = resp.json()
    prov = data.get("feature_provenance")
    assert prov is not None, "feature_provenance missing from /risk/current/C03"
    assert prov.get("slope") == "REAL_DEM"
    assert prov.get("elevation") == "REAL_DEM"
    assert prov.get("rainfall") == "SAMPLE_MOCK"
    assert prov.get("soil_wetness") == "SAMPLE_MOCK"
    # Slope reported should be ~22°, not 42°
    assert data.get("slope", 100) < 40, f"Expected real slope ~22°, got {data.get('slope')}"


# ─── 15. /risk/forecast/C03 has feature_provenance ───────────────────────────

def test_risk_forecast_c03_has_provenance(test_client):
    """GET /risk/forecast/C03 exposes feature_provenance with REAL_DEM slope."""
    resp = test_client.get("/risk/forecast/C03")
    assert resp.status_code == 200
    data = resp.json()
    prov = data.get("feature_provenance")
    assert prov is not None, "feature_provenance missing from /risk/forecast/C03"
    assert prov.get("slope") == "REAL_DEM"
    assert prov.get("elevation") == "REAL_DEM"
    assert prov.get("rainfall") == "SAMPLE_MOCK"
    assert prov.get("soil_wetness") == "SAMPLE_MOCK"


# ─── 16. Boundary cell slope calculation (continuous vs masked DEM) ─────────

def test_boundary_cell_receives_slope_from_outside_terrain():
    """
    Proves that a polygon-boundary cell receives a valid slope value using terrain
    immediately outside the zone polygon, demonstrating that slopes are computed
    on the continuous DEM before zonal masking (preventing artificial boundary dropouts).
    """
    import numpy as np
    from backend.services.terrain_processor import compute_metric_slope_and_aspect

    # 1. Create a continuous 10x10 synthetic DEM (an inclined plane z = 2*x + 1*y in 30m cells)
    dx, dy = 30.0, 30.0
    y_coords, x_coords = np.mgrid[0:10, 0:10]
    synthetic_dem = (2.0 * x_coords * dx + 1.0 * y_coords * dy).astype(np.float32)

    # 2. Define an interior 6x6 polygon box: rows 2..7, cols 2..7 (total 36 cells)
    row_start, row_end = 2, 8
    col_start, col_end = 2, 8
    poly_mask = np.zeros((10, 10), dtype=bool)
    poly_mask[row_start:row_end, col_start:col_end] = True
    assert poly_mask.sum() == 36

    # --- METHOD A: Flawed approach (masking to nodata BEFORE slope computation) ---
    masked_dem_flawed = np.where(poly_mask, synthetic_dem, -999999.0)
    flawed_slope, _, _ = compute_metric_slope_and_aspect(
        masked_dem_flawed, dx=dx, dy=dy, nodata=-999999.0
    )
    in_polygon_flawed = flawed_slope[poly_mask]
    valid_flawed_count = int((~np.isnan(in_polygon_flawed)).sum())
    # In flawed method, the 20 boundary cells of the 6x6 box see nodata and become NaN.
    # Only the inner 4x4 (16 cells) survive:
    assert valid_flawed_count == 16, f"Flawed method should only compute 16 interior cells, got {valid_flawed_count}"

    # --- METHOD B: Correct approach (computing slope on continuous DEM FIRST, then masking) ---
    continuous_slope, _, _ = compute_metric_slope_and_aspect(
        synthetic_dem, dx=dx, dy=dy, nodata=-999999.0
    )
    in_polygon_correct = continuous_slope[poly_mask]
    valid_correct_count = int((~np.isnan(in_polygon_correct)).sum())
    # All 36 cells of the polygon have valid slope because the Horn kernel used outside terrain:
    assert valid_correct_count == 36, f"Continuous method should have all 36 cells valid, got {valid_correct_count}"

    # All boundary cells have the true continuous slope value of the plane:
    expected_slope_deg = float(np.degrees(np.arctan(np.sqrt(2.0**2 + 1.0**2))))
    assert np.allclose(in_polygon_correct, expected_slope_deg, atol=0.01)


def test_all_zones_have_zero_artificial_boundary_dropouts(zones):
    """
    In the real Copernicus DEM zonal statistics, every in-zone DEM cell
    must have a valid slope value (valid_slope_pixel_count == zone_pixel_count).
    There should be 0 boundary dropouts across all 25 pilot zones.
    """
    for zid, z in zones.items():
        zc = z.get("zone_pixel_count", z.get("valid_pixel_count"))
        sc = z.get("valid_slope_pixel_count", z.get("valid_pixel_count"))
        assert zc == sc, (
            f"Zone {zid} has slope dropouts: {zc} zone cells vs {sc} slope cells "
            f"({zc - sc} cells dropped)"
        )
