"""Build the deterministic Mizoram 90 m static terrain predictor stack.

This offline utility consumes validated Copernicus GLO-30 source COGs. It is
not imported by the TerraSense application and does not train a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyproj
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.transform import Affine, from_origin
from rasterio.warp import Resampling, reproject
from shapely.geometry import mapping
from shapely.ops import transform as shapely_transform

from acquire_mizoram_dem import (
    DEFAULT_BOUNDARY,
    DEFAULT_RAW_DIR,
    DERIVATIVE_ATTRIBUTION,
    PRODUCT,
    PRODUCT_IDENTIFIER,
    PRODUCT_RELEASE,
    derive_tile_plan,
    load_mizoram_geometry,
    sha256_file,
    validate_dem_tile,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT
    / "local-data"
    / "susceptibility"
    / "copernicus-glo30-2021"
    / "derived"
    / "terrain-v1"
)
TARGET_CRS = "EPSG:32646"
TARGET_RESOLUTION_METRES = 90.0
PROCESSING_BUFFER_METRES = 270.0
OUTPUT_NODATA = -9999.0
PREDICTOR_NAMES = (
    "elevation_m",
    "slope_deg",
    "aspect_sin",
    "aspect_cos",
    "curvature_laplacian_per_m",
    "tpi_3x3_m",
)


class PredictorError(RuntimeError):
    """Raised when the predictor build cannot satisfy its spatial contract."""


@dataclass(frozen=True)
class GridSpec:
    crs: str
    resolution: float
    buffer_metres: float
    transform: Affine
    width: int
    height: int
    bounds: tuple[float, float, float, float]


def snapped_grid(
    geometry_wgs84,
    *,
    target_crs: str = TARGET_CRS,
    resolution: float = TARGET_RESOLUTION_METRES,
    buffer_metres: float = PROCESSING_BUFFER_METRES,
) -> tuple[GridSpec, Any]:
    transformer = pyproj.Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    geometry_projected = shapely_transform(transformer.transform, geometry_wgs84)
    minx, miny, maxx, maxy = geometry_projected.bounds
    left = math.floor((minx - buffer_metres) / resolution) * resolution
    bottom = math.floor((miny - buffer_metres) / resolution) * resolution
    right = math.ceil((maxx + buffer_metres) / resolution) * resolution
    top = math.ceil((maxy + buffer_metres) / resolution) * resolution
    width = int(round((right - left) / resolution))
    height = int(round((top - bottom) / resolution))
    if width <= 0 or height <= 0:
        raise PredictorError("The snapped target grid is empty")
    transform = from_origin(left, top, resolution, resolution)
    return (
        GridSpec(
            crs=target_crs,
            resolution=resolution,
            buffer_metres=buffer_metres,
            transform=transform,
            width=width,
            height=height,
            bounds=(left, bottom, right, top),
        ),
        geometry_projected,
    )


def valid_mask(array: np.ndarray, nodata: float | None = None) -> np.ndarray:
    valid = np.isfinite(array)
    if nodata is not None and not math.isnan(nodata):
        valid &= array != nodata
    return valid


def terrain_derivatives(
    elevation: np.ndarray,
    *,
    resolution: float = TARGET_RESOLUTION_METRES,
    nodata: float = OUTPUT_NODATA,
    flat_tolerance: float = 1e-12,
) -> dict[str, np.ndarray]:
    if elevation.ndim != 2 or min(elevation.shape) < 3:
        raise PredictorError("Terrain derivatives require a two-dimensional grid of at least 3x3")
    source = elevation.astype(np.float64, copy=False)
    source_valid = valid_mask(source, nodata)
    windows = [source[row : source.shape[0] - 2 + row, col : source.shape[1] - 2 + col]
               for row in range(3) for col in range(3)]
    valid_windows = [
        source_valid[row : source.shape[0] - 2 + row, col : source.shape[1] - 2 + col]
        for row in range(3)
        for col in range(3)
    ]
    complete = np.logical_and.reduce(valid_windows)
    z_nw, z_n, z_ne, z_w, z_c, z_e, z_sw, z_s, z_se = windows

    dz_dx = ((z_ne + 2 * z_e + z_se) - (z_nw + 2 * z_w + z_sw)) / (8 * resolution)
    dz_dy_north = ((z_nw + 2 * z_n + z_ne) - (z_sw + 2 * z_s + z_se)) / (
        8 * resolution
    )
    magnitude = np.hypot(dz_dx, dz_dy_north)
    slope = np.degrees(np.arctan(magnitude))

    # Aspect is the downslope direction, clockwise from grid north.
    aspect = np.mod(np.arctan2(-dz_dx, -dz_dy_north), 2 * np.pi)
    aspect_sin = np.sin(aspect)
    aspect_cos = np.cos(aspect)
    flat = magnitude <= flat_tolerance
    aspect_sin[flat] = 0.0
    aspect_cos[flat] = 0.0

    curvature = (
        (z_e - 2 * z_c + z_w) / resolution**2
        + (z_n - 2 * z_c + z_s) / resolution**2
    )
    tpi = z_c - ((z_nw + z_n + z_ne + z_w + z_e + z_sw + z_s + z_se) / 8.0)

    shape = elevation.shape
    results = {
        name: np.full(shape, nodata, dtype=np.float32)
        for name in PREDICTOR_NAMES[1:]
    }
    values = {
        "slope_deg": slope,
        "aspect_sin": aspect_sin,
        "aspect_cos": aspect_cos,
        "curvature_laplacian_per_m": curvature,
        "tpi_3x3_m": tpi,
    }
    for name, interior_values in values.items():
        interior = results[name][1:-1, 1:-1]
        interior[complete] = interior_values[complete].astype(np.float32)
    return results


def apply_boundary_mask(
    arrays: dict[str, np.ndarray],
    geometry_projected,
    transform: Affine,
    *,
    nodata: float = OUTPUT_NODATA,
) -> dict[str, np.ndarray]:
    first = next(iter(arrays.values()))
    inside = geometry_mask(
        [mapping(geometry_projected)],
        out_shape=first.shape,
        transform=transform,
        invert=True,
        all_touched=False,
    )
    masked: dict[str, np.ndarray] = {}
    for name, array in arrays.items():
        result = array.astype(np.float32, copy=True)
        result[~inside] = nodata
        masked[name] = result
    return masked


def _mosaic_sources(source_paths: list[Path]) -> tuple[np.ndarray, Affine, Any]:
    datasets = [rasterio.open(path) for path in source_paths]
    try:
        crs_values = {dataset.crs for dataset in datasets}
        if len(crs_values) != 1 or next(iter(crs_values)).to_epsg() != 4326:
            raise PredictorError("All source tiles must use EPSG:4326")
        mosaic, transform = merge(datasets, masked=True, method="first")
        band = mosaic[0]
        filled = band.filled(np.nan).astype(np.float32)
        return filled, transform, datasets[0].crs
    finally:
        for dataset in datasets:
            dataset.close()


def reproject_elevation_to_grid(
    source_paths: list[Path],
    grid: GridSpec,
) -> np.ndarray:
    source, source_transform, source_crs = _mosaic_sources(source_paths)
    destination = np.full((grid.height, grid.width), OUTPUT_NODATA, dtype=np.float32)
    reproject(
        source=source,
        destination=destination,
        src_transform=source_transform,
        src_crs=source_crs,
        # The mosaic is a masked array filled with NaN, regardless of the
        # source file's declared nodata marker.
        src_nodata=np.nan,
        dst_transform=grid.transform,
        dst_crs=grid.crs,
        dst_nodata=OUTPUT_NODATA,
        resampling=Resampling.average,
        init_dest_nodata=True,
        num_threads=1,
    )
    return destination


def _output_profile(grid: GridSpec) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "driver": "GTiff",
        "width": grid.width,
        "height": grid.height,
        "count": len(PREDICTOR_NAMES),
        "dtype": "float32",
        "crs": grid.crs,
        "transform": grid.transform,
        "nodata": OUTPUT_NODATA,
        "compress": "DEFLATE",
        "predictor": 3,
        "zlevel": 9,
        "interleave": "band",
        "BIGTIFF": "IF_SAFER",
    }
    if grid.width >= 16 and grid.height >= 16:
        profile.update(tiled=True, blockxsize=min(256, (grid.width // 16) * 16), blockysize=min(256, (grid.height // 16) * 16))
    return profile


def write_predictor_stack(
    path: Path,
    arrays: dict[str, np.ndarray],
    grid: GridSpec,
) -> None:
    if tuple(arrays) != PREDICTOR_NAMES:
        raise PredictorError(f"Predictors must be ordered as {PREDICTOR_NAMES}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.tif")
    try:
        with rasterio.open(temporary, "w", **_output_profile(grid)) as destination:
            for index, name in enumerate(PREDICTOR_NAMES, start=1):
                array = arrays[name]
                if array.shape != (grid.height, grid.width):
                    raise PredictorError(f"{name} shape {array.shape} does not match the grid")
                destination.write(array.astype(np.float32, copy=False), index)
                destination.set_band_description(index, name)
            destination.update_tags(
                product="TerraSense Mizoram terrain predictors v1",
                source_product=PRODUCT_IDENTIFIER,
                source_release=PRODUCT_RELEASE,
                horizontal_crs=grid.crs,
                vertical_datum="EGM2008 (EPSG:3855), retained without vertical transformation",
                resolution_metres=str(grid.resolution),
                processing_buffer_metres=str(grid.buffer_metres),
                elevation_resampling="GDAL average resampling from GLO-30 to the fixed 90 m grid",
                derivative_attribution=DERIVATIVE_ATTRIBUTION,
            )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _software_versions() -> dict[str, str]:
    return {
        "numpy": np.__version__,
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "pyproj": pyproj.__version__,
        "proj": pyproj.proj_version_str,
    }


def build_manifest(
    grid: GridSpec,
    source_paths: list[Path],
    output_path: Path,
    boundary_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "DERIVED_TERRAIN_PREDICTORS_NO_MODEL",
        "source": {
            "product": PRODUCT,
            "product_identifier": PRODUCT_IDENTIFIER,
            "release": PRODUCT_RELEASE,
            "vertical_datum": "EGM2008 (EPSG:3855)",
            "tiles": [
                {"filename": path.name, "sha256": sha256_file(path)}
                for path in sorted(source_paths, key=lambda item: item.name)
            ],
        },
        "boundary": {
            "path": "data/geodata/ner/states.geojson",
            "state_id": "IN-MZ",
            "sha256": sha256_file(boundary_path),
            "mask_rule": "pixel centre inside current Mizoram ADM1 geometry; all_touched=false",
        },
        "grid": {
            "crs": grid.crs,
            "resolution_metres": grid.resolution,
            "buffer_metres": grid.buffer_metres,
            "origin_rule": "bounds expanded by 270 m and snapped outward to multiples of 90 m from the EPSG:32646 origin",
            "transform": list(grid.transform)[:6],
            "bounds": list(grid.bounds),
            "width": grid.width,
            "height": grid.height,
            "nodata": OUTPUT_NODATA,
        },
        "predictors": {
            "elevation_m": "GDAL average resampling of GLO-30 elevations to 90 m before derivatives",
            "slope_deg": "Horn 3x3 gradient in degrees on the final 90 m elevation grid",
            "aspect_sin": "sine of clockwise-from-north downslope Horn aspect; zero on flat cells",
            "aspect_cos": "cosine of clockwise-from-north downslope Horn aspect; zero on flat cells",
            "curvature_laplacian_per_m": "(zE-2*zC+zW)/90^2 + (zN-2*zC+zS)/90^2",
            "tpi_3x3_m": "zC minus the arithmetic mean of all eight adjacent 90 m cells",
            "neighbourhood_rule": "all nine cells must be valid; otherwise derivative nodata",
        },
        "output": {
            "filename": output_path.name,
            "sha256": sha256_file(output_path),
            "dtype": "float32",
            "compression": "DEFLATE level 9 with floating-point predictor",
            "bands": list(PREDICTOR_NAMES),
            "derivative_attribution": DERIVATIVE_ATTRIBUTION,
        },
        "software": _software_versions(),
    }


def atomic_write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def resolve_source_paths(raw_dir: Path, geometry) -> list[Path]:
    paths: list[Path] = []
    for tile in derive_tile_plan(geometry):
        path = raw_dir / f"{tile.tile_id}.tif"
        if not path.is_file():
            raise PredictorError(f"Required source tile is missing: {path}")
        validate_dem_tile(path, tile.bounds)
        paths.append(path)
    return paths


def build(
    *,
    boundary_path: Path,
    raw_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    geometry = load_mizoram_geometry(boundary_path)
    source_paths = resolve_source_paths(raw_dir, geometry)
    grid, geometry_projected = snapped_grid(geometry)
    elevation_buffered = reproject_elevation_to_grid(source_paths, grid)
    derivatives = terrain_derivatives(elevation_buffered)
    arrays = {"elevation_m": elevation_buffered.astype(np.float32), **derivatives}
    arrays = apply_boundary_mask(arrays, geometry_projected, grid.transform)

    if output_dir.exists():
        raise PredictorError(f"Refusing to replace existing output directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="terrasense-phase5b0-", dir=output_dir.parent) as temp:
        temporary_dir = Path(temp) / output_dir.name
        temporary_dir.mkdir()
        output_path = temporary_dir / "mizoram_terrain_predictors_v1.tif"
        write_predictor_stack(output_path, arrays, grid)
        manifest = build_manifest(grid, source_paths, output_path, boundary_path)
        atomic_write_manifest(temporary_dir / "manifest.json", manifest)
        os.replace(temporary_dir, output_dir)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    try:
        manifest = build(
            boundary_path=args.boundary.resolve(),
            raw_dir=args.raw_dir.resolve(),
            output_dir=args.output_dir.resolve(),
        )
    except (PredictorError, OSError, rasterio.errors.RasterioError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "output_sha256": manifest["output"]["sha256"],
                "grid": manifest["grid"],
                "bands": manifest["output"]["bands"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
