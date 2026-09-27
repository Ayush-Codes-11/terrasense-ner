from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
import urllib.error
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import acquire_mizoram_dem as acquisition
import build_mizoram_terrain_predictors as predictors


EXPECTED_TILES = [
    "Copernicus_DSM_COG_10_N21_00_E092_00_DEM",
    "Copernicus_DSM_COG_10_N21_00_E093_00_DEM",
    "Copernicus_DSM_COG_10_N22_00_E092_00_DEM",
    "Copernicus_DSM_COG_10_N22_00_E093_00_DEM",
    "Copernicus_DSM_COG_10_N23_00_E092_00_DEM",
    "Copernicus_DSM_COG_10_N23_00_E093_00_DEM",
    "Copernicus_DSM_COG_10_N24_00_E092_00_DEM",
    "Copernicus_DSM_COG_10_N24_00_E093_00_DEM",
]


def _fake_remote(url: str) -> acquisition.RemoteMetadata:
    tile_id = url.split("/")[-2]
    index = EXPECTED_TILES.index(tile_id)
    return acquisition.RemoteMetadata(
        content_length=1000 + index,
        etag=f'"etag-{index}"',
        last_modified="Mon, 09 May 2022 14:00:00 GMT",
        content_type="image/tiff",
    )


def _write_small_raster(
    path: Path,
    data: np.ndarray,
    *,
    crs: str = "EPSG:4326",
    transform=None,
    nodata: float | None = None,
) -> None:
    transform = transform or from_origin(92, 22, 0.25, 0.25)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[1],
        height=data.shape[0],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as destination:
        destination.write(data.astype(np.float32), 1)


def test_current_mizoram_geometry_produces_exact_eight_tile_plan():
    geometry = acquisition.load_mizoram_geometry()
    plan = acquisition.derive_tile_plan(geometry)
    assert [tile.tile_id for tile in plan] == EXPECTED_TILES
    assert plan[0].bounds == (92, 21, 93, 22)
    assert plan[-1].bounds == (93, 24, 94, 25)


def test_plan_manifest_is_deterministically_ordered(tmp_path: Path):
    first = acquisition.build_plan_manifest(metadata_fetcher=_fake_remote)
    second = acquisition.build_plan_manifest(metadata_fetcher=_fake_remote)
    assert first == second
    assert [tile["tile_id"] for tile in first["tiles"]] == EXPECTED_TILES
    assert first["total_expected_size_bytes"] == sum(range(1000, 1008))
    assert first["raster_bytes_downloaded"] == 0
    assert all(tile["local_sha256"] is None for tile in first["tiles"])
    one = tmp_path / "one.json"
    two = tmp_path / "two.json"
    acquisition.atomic_write_json(one, first)
    acquisition.atomic_write_json(two, second)
    assert one.read_bytes() == two.read_bytes()


def test_default_dry_run_downloads_zero_raster_bytes(monkeypatch, tmp_path: Path):
    methods: list[str] = []

    def metadata(url: str, timeout: int = 20):
        methods.append("HEAD")
        return _fake_remote(url)

    monkeypatch.setattr(acquisition, "probe_remote_metadata", metadata)
    plan_path = tmp_path / "plan.json"
    raw_dir = tmp_path / "raw"
    result = acquisition.run(
        boundary=acquisition.DEFAULT_BOUNDARY,
        plan_manifest=plan_path,
        raw_dir=raw_dir,
        acquisition_manifest=tmp_path / "acquired.json",
        download=False,
        confirm_download=False,
        timeout=1,
    )
    assert methods == ["HEAD"] * 8
    assert result["raster_bytes_downloaded"] == 0
    assert not raw_dir.exists()
    assert plan_path.is_file()


def test_remote_metadata_changes_are_reported(monkeypatch, tmp_path: Path):
    plan_path = tmp_path / "plan.json"
    previous = acquisition.build_plan_manifest(metadata_fetcher=_fake_remote)
    acquisition.atomic_write_json(plan_path, previous)

    def changed(url: str, timeout: int = 20):
        original = _fake_remote(url)
        if EXPECTED_TILES[0] in url:
            return acquisition.RemoteMetadata(
                original.content_length + 1,
                '"changed"',
                original.last_modified,
                original.content_type,
            )
        return original

    monkeypatch.setattr(acquisition, "probe_remote_metadata", changed)
    result = acquisition.run(
        boundary=acquisition.DEFAULT_BOUNDARY,
        plan_manifest=plan_path,
        raw_dir=tmp_path / "raw",
        acquisition_manifest=tmp_path / "acquired.json",
        download=False,
        confirm_download=False,
        timeout=1,
    )
    assert any("expected_size_bytes" in message for message in result["remote_metadata_changes"])
    assert any("provider_object_etag" in message for message in result["remote_metadata_changes"])


def test_metadata_timeout_is_a_clear_acquisition_error(monkeypatch):
    def timeout(*args, **kwargs):
        raise urllib.error.URLError(TimeoutError("bounded timeout"))

    monkeypatch.setattr(acquisition, "open_trusted_request", timeout)
    with pytest.raises(acquisition.AcquisitionError, match="Metadata request failed"):
        acquisition.probe_remote_metadata(
            f"{acquisition.SOURCE_BASE_URL}/{EXPECTED_TILES[0]}/{EXPECTED_TILES[0]}.tif",
            timeout=1,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://copernicus-dem-30m.s3.amazonaws.com/tile/tile.tif",
        "https://example.invalid/tile/tile.tif",
        "https://copernicus-dem-30m.s3.amazonaws.com/../secret/secret.tif",
        "https://copernicus-dem-30m.s3.amazonaws.com/%2e%2e/secret/secret.tif",
    ],
)
def test_source_url_allowlist_rejects_untrusted_or_unsafe_paths(url: str):
    with pytest.raises(acquisition.AcquisitionError):
        acquisition.validate_source_url(url)


def test_source_url_requires_exact_tile_path():
    tile_id = EXPECTED_TILES[0]
    url = f"{acquisition.SOURCE_BASE_URL}/{tile_id}/{tile_id}.tif"
    assert acquisition.validate_source_url(url, tile_id) == tile_id
    with pytest.raises(acquisition.AcquisitionError, match="does not match"):
        acquisition.validate_source_url(url, EXPECTED_TILES[1])


def test_content_range_requires_exact_start_end_and_total():
    acquisition.validate_content_range("bytes 4-9/10", offset=4, expected_size=10)
    for value in ("bytes 3-9/10", "bytes 4-9/11", "bytes 4-10/10", "bytes 4-*/10"):
        with pytest.raises(acquisition.AcquisitionError):
            acquisition.validate_content_range(value, offset=4, expected_size=10)


def test_redirects_are_explicitly_rejected():
    request = acquisition.urllib.request.Request(
        f"{acquisition.SOURCE_BASE_URL}/{EXPECTED_TILES[0]}/{EXPECTED_TILES[0]}.tif"
    )
    with pytest.raises(acquisition.AcquisitionError, match="Refusing redirect"):
        acquisition.RejectRedirectHandler().redirect_request(
            request, None, 302, "Found", {}, "https://example.invalid/tile.tif"
        )


@pytest.mark.parametrize("content_type", ["text/html", "application/xml", "application/json"])
def test_html_xml_and_json_responses_are_rejected(content_type: str):
    with pytest.raises(acquisition.AcquisitionError, match="not a GeoTIFF"):
        acquisition.validate_response_type(content_type, b"<htm")
    with pytest.raises(acquisition.AcquisitionError, match="TIFF signature"):
        acquisition.validate_response_type("application/octet-stream", b"NOPE")


def test_existing_file_is_validated_and_checksum_mismatch_refuses_overwrite(tmp_path: Path):
    path = tmp_path / "tile.tif"
    _write_small_raster(path, np.arange(16, dtype=np.float32).reshape(4, 4))
    tile = {
        "expected_size_bytes": path.stat().st_size,
        "bounds_epsg4326": [92, 21, 93, 22],
    }
    actual = acquisition.validate_existing_file(path, tile, expected_dimension=4)
    assert actual == hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(acquisition.AcquisitionError, match="SHA-256 differs"):
        acquisition.validate_existing_file(
            path,
            tile,
            previous_sha256="0" * 64,
            expected_dimension=4,
        )
    wrong_size = {**tile, "expected_size_bytes": path.stat().st_size + 1}
    with pytest.raises(acquisition.AcquisitionError, match="Refusing to overwrite"):
        acquisition.validate_existing_file(path, wrong_size, expected_dimension=4)


def test_completed_partial_is_validated_without_another_request(monkeypatch, tmp_path: Path):
    destination = tmp_path / "tile.tif"
    partial = destination.with_suffix(".tif.part")
    partial.write_bytes(b"II*\x00complete")
    tile_id = EXPECTED_TILES[0]
    tile = {
        "tile_id": tile_id,
        "url": f"{acquisition.SOURCE_BASE_URL}/{tile_id}/{tile_id}.tif",
        "expected_size_bytes": partial.stat().st_size,
        "bounds_epsg4326": [92, 21, 93, 22],
    }
    monkeypatch.setattr(acquisition, "validate_dem_tile", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        acquisition,
        "open_trusted_request",
        lambda *args, **kwargs: pytest.fail("a complete partial must not make a request"),
    )
    acquisition._download_one(tile, destination, timeout=1)
    assert destination.read_bytes() == b"II*\x00complete"
    assert not partial.exists()


def test_server_ignoring_range_restarts_atomically(monkeypatch, tmp_path: Path):
    destination = tmp_path / "tile.tif"
    partial = destination.with_suffix(".tif.part")
    partial.write_bytes(b"II*\x00old")
    complete = b"II*\x00replacement"
    tile_id = EXPECTED_TILES[0]
    tile = {
        "tile_id": tile_id,
        "url": f"{acquisition.SOURCE_BASE_URL}/{tile_id}/{tile_id}.tif",
        "expected_size_bytes": len(complete),
        "bounds_epsg4326": [92, 21, 93, 22],
    }

    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Type": "image/tiff"}

        def getcode(self):
            return self.status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(
        acquisition,
        "open_trusted_request",
        lambda request, timeout: Response(complete),
    )
    monkeypatch.setattr(acquisition, "validate_dem_tile", lambda *args, **kwargs: {})
    acquisition._download_one(tile, destination, timeout=1)
    assert destination.read_bytes() == complete
    assert not partial.exists()


def test_mosaic_normalizes_declared_nodata_to_nan(tmp_path: Path):
    path = tmp_path / "nodata.tif"
    data = np.arange(16, dtype=np.float32).reshape(4, 4)
    data[1, 1] = -32767.0
    _write_small_raster(path, data, nodata=-32767.0)
    mosaic, _, _ = predictors._mosaic_sources([path])
    assert np.isnan(mosaic[1, 1])


def test_download_requires_both_explicit_flags(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(acquisition, "probe_remote_metadata", lambda url, timeout=20: _fake_remote(url))
    with pytest.raises(acquisition.AcquisitionError, match="both --download and --confirm-download"):
        acquisition.run(
            boundary=acquisition.DEFAULT_BOUNDARY,
            plan_manifest=tmp_path / "plan.json",
            raw_dir=tmp_path / "raw",
            acquisition_manifest=tmp_path / "acquired.json",
            download=True,
            confirm_download=False,
            timeout=1,
        )


def test_download_refuses_missing_licence_acceptance(tmp_path: Path):
    plan = acquisition.build_plan_manifest(metadata_fetcher=_fake_remote)
    plan["licence"]["accepted_by"] = None
    with pytest.raises(acquisition.AcquisitionError, match="acceptance is not recorded"):
        acquisition.acquire_tiles(plan, tmp_path / "raw", tmp_path / "manifest.json")


def test_download_refuses_insufficient_disk_space(monkeypatch, tmp_path: Path):
    plan = acquisition.build_plan_manifest(metadata_fetcher=_fake_remote)
    monkeypatch.setattr(
        acquisition.shutil,
        "disk_usage",
        lambda path: shutil._ntuple_diskusage(total=100, used=99, free=1),
    )
    with pytest.raises(acquisition.AcquisitionError, match="Insufficient disk space"):
        acquisition.acquire_tiles(plan, tmp_path / "raw", tmp_path / "manifest.json")


def test_acquire_rejects_unsafe_tile_id_before_existing_file_lookup(tmp_path: Path):
    plan = acquisition.build_plan_manifest(metadata_fetcher=_fake_remote)
    plan["tiles"][0]["tile_id"] = "../../outside"
    with pytest.raises(acquisition.AcquisitionError):
        acquisition.acquire_tiles(plan, tmp_path / "raw", tmp_path / "manifest.json")


def test_grid_is_epsg32646_at_90_metres_with_snapped_origin_and_buffer():
    geometry = acquisition.load_mizoram_geometry()
    grid, projected = predictors.snapped_grid(geometry)
    assert grid.crs == "EPSG:32646"
    assert grid.resolution == 90.0
    assert grid.buffer_metres == 270.0
    assert grid.transform.a == 90.0
    assert grid.transform.e == -90.0
    assert grid.bounds[0] % 90 == 0
    assert grid.bounds[1] % 90 == 0
    assert grid.bounds[2] % 90 == 0
    assert grid.bounds[3] % 90 == 0
    assert grid.bounds[0] <= projected.bounds[0] - 270
    assert grid.bounds[1] <= projected.bounds[1] - 270
    assert grid.bounds[2] >= projected.bounds[2] + 270
    assert grid.bounds[3] >= projected.bounds[3] + 270
    assert (grid.width, grid.height) == (1342, 3180)


def test_processing_buffer_expands_grid_by_at_least_six_cells():
    geometry = acquisition.load_mizoram_geometry()
    buffered, _ = predictors.snapped_grid(geometry, buffer_metres=270)
    unbuffered, _ = predictors.snapped_grid(geometry, buffer_metres=0)
    assert buffered.width >= unbuffered.width + 6
    assert buffered.height >= unbuffered.height + 6


def test_synthetic_elevation_reprojects_to_aligned_utm_grid(tmp_path: Path):
    source = tmp_path / "constant.tif"
    _write_small_raster(
        source,
        np.full((6, 6), 123.0, dtype=np.float32),
        transform=from_origin(92.7, 23.706, 0.001, 0.001),
    )
    grid, _ = predictors.snapped_grid(
        box(92.701, 23.701, 92.705, 23.705),
        buffer_metres=0,
    )
    result = predictors.reproject_elevation_to_grid([source], grid)
    finite = result[result != predictors.OUTPUT_NODATA]
    assert finite.size > 0
    assert np.allclose(finite, 123.0, atol=1e-5)
    assert grid.crs == "EPSG:32646"
    assert grid.transform.a == 90.0
    assert grid.transform.e == -90.0


def test_flat_dem_has_zero_slope_and_neutral_aspect_vector():
    elevation = np.full((5, 5), 100.0, dtype=np.float32)
    result = predictors.terrain_derivatives(elevation)
    assert np.all(result["slope_deg"][1:-1, 1:-1] == 0)
    assert np.all(result["aspect_sin"][1:-1, 1:-1] == 0)
    assert np.all(result["aspect_cos"][1:-1, 1:-1] == 0)


@pytest.mark.parametrize(
    ("elevation", "expected_sin", "expected_cos"),
    [
        (np.tile(np.arange(5) * 90.0, (5, 1)), -1.0, 0.0),  # rises east; faces west
        (np.tile(-np.arange(5)[:, None] * 90.0, (1, 5)), 0.0, -1.0),  # rises north; faces south
        (np.tile(-np.arange(5) * 90.0, (5, 1)), 1.0, 0.0),  # rises west; faces east
        (np.tile(np.arange(5)[:, None] * 90.0, (1, 5)), 0.0, 1.0),  # rises south; faces north
    ],
)
def test_known_planar_slope_and_aspect_convention(
    elevation: np.ndarray, expected_sin: float, expected_cos: float
):
    result = predictors.terrain_derivatives(elevation.astype(np.float32))
    centre = (2, 2)
    assert result["slope_deg"][centre] == pytest.approx(45.0)
    assert result["aspect_sin"][centre] == pytest.approx(expected_sin, abs=1e-6)
    assert result["aspect_cos"][centre] == pytest.approx(expected_cos, abs=1e-6)


def test_curvature_and_tpi_definitions_are_fixed():
    elevation = np.zeros((5, 5), dtype=np.float32)
    elevation[2, 2] = 8.0
    result = predictors.terrain_derivatives(elevation)
    assert result["curvature_laplacian_per_m"][2, 2] == pytest.approx(-32 / 90**2)
    assert result["tpi_3x3_m"][2, 2] == pytest.approx(8.0)


def test_nodata_propagates_to_every_derivative_neighbourhood():
    elevation = np.full((5, 5), 100.0, dtype=np.float32)
    elevation[1, 1] = predictors.OUTPUT_NODATA
    result = predictors.terrain_derivatives(elevation)
    for name, array in result.items():
        assert array[2, 2] == predictors.OUTPUT_NODATA, name


def test_final_boundary_mask_uses_pixel_centres():
    transform = from_origin(0, 360, 90, 90)
    arrays = {
        name: np.ones((4, 4), dtype=np.float32)
        for name in predictors.PREDICTOR_NAMES
    }
    masked = predictors.apply_boundary_mask(arrays, box(90, 90, 270, 270), transform)
    expected_inside = np.zeros((4, 4), dtype=bool)
    expected_inside[1:3, 1:3] = True
    for array in masked.values():
        assert np.all(array[expected_inside] == 1)
        assert np.all(array[~expected_inside] == predictors.OUTPUT_NODATA)


def test_predictor_geotiff_is_float32_metadata_complete_and_deterministic(tmp_path: Path):
    grid = predictors.GridSpec(
        crs="EPSG:32646",
        resolution=90.0,
        buffer_metres=270.0,
        transform=from_origin(0, 1800, 90, 90),
        width=20,
        height=20,
        bounds=(0, 0, 1800, 1800),
    )
    arrays = {
        name: np.full((20, 20), index, dtype=np.float32)
        for index, name in enumerate(predictors.PREDICTOR_NAMES, start=1)
    }
    first = tmp_path / "first.tif"
    second = tmp_path / "second.tif"
    predictors.write_predictor_stack(first, arrays, grid)
    predictors.write_predictor_stack(second, arrays, grid)
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(second.read_bytes()).hexdigest()
    with rasterio.open(first) as dataset:
        assert dataset.crs.to_epsg() == 32646
        assert dataset.res == (90.0, 90.0)
        assert dataset.nodata == predictors.OUTPUT_NODATA
        assert dataset.dtypes == ("float32",) * 6
        assert dataset.descriptions == predictors.PREDICTOR_NAMES
        assert dataset.compression.name == "deflate"
        assert dataset.tags()["vertical_datum"].startswith("EGM2008")


def test_no_forbidden_dynamic_or_operational_predictors():
    assert predictors.PREDICTOR_NAMES == (
        "elevation_m",
        "slope_deg",
        "aspect_sin",
        "aspect_cos",
        "curvature_laplacian_per_m",
        "tpi_3x3_m",
    )


def test_large_training_and_raster_locations_are_git_ignored():
    candidates = [
        ".venv-phase5b0/probe",
        "local-data/susceptibility/raw/tile.tif",
        "local-data/susceptibility/work/mosaic.vrt",
        "local-data/susceptibility/derived/predictors.tiff",
        "local-data/susceptibility/training/samples.parquet",
        "artifacts/ml/susceptibility/model.joblib",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--", *candidates],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout.splitlines() == candidates
