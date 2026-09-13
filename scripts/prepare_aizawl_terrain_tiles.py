"""Build deterministic Aizawl Terrarium tiles from the validated Copernicus DEM.

The source GeoTIFF remains outside the deployable frontend. Output pixels use
the Terrarium formula ``height = R * 256 + G + B / 256 - 32768``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "real" / "terrain" / "copernicus_glo30_aizawl.tif"
DEFAULT_OUTPUT = REPO_ROOT / "frontend" / "public" / "terrain" / "aizawl" / "v1"
EXPECTED_SOURCE_SHA256 = "dcbfe1a282feade4c77bfbf0717bae7126a63eca31524fae1e61a974a7924ed9"
TILE_SIZE = 256
MIN_ZOOM = 8
MAX_ZOOM = 13
EDGE_PADDING_PIXELS = 1
ATTRIBUTION = (
    "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA; all rights reserved. "
    "Distributed via AWS Open Data/Sinergise."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def lon_to_tile_x(lon: float, zoom: int) -> int:
    return min((1 << zoom) - 1, max(0, math.floor((lon + 180.0) / 360.0 * (1 << zoom))))


def lat_to_tile_y(lat: float, zoom: int) -> int:
    value = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0
    return min((1 << zoom) - 1, max(0, math.floor(value * (1 << zoom))))


def tile_ranges(bounds: tuple[float, float, float, float], zoom: int) -> tuple[int, int, int, int]:
    west, south, east, north = bounds
    return (
        lon_to_tile_x(west, zoom),
        lon_to_tile_x(np.nextafter(east, west), zoom),
        lat_to_tile_y(np.nextafter(north, south), zoom),
        lat_to_tile_y(south, zoom),
    )


def sample_source(
    source: np.ndarray,
    transform: rasterio.Affine,
    lons: np.ndarray,
    lats: np.ndarray,
) -> np.ndarray:
    """Bilinearly sample source pixels, clamping only beyond source edges."""
    cols = (lons - transform.c) / transform.a - 0.5
    rows = (lats - transform.f) / transform.e - 0.5
    cols = np.clip(cols, 0.0, source.shape[1] - 1.0)
    rows = np.clip(rows, 0.0, source.shape[0] - 1.0)
    c0 = np.floor(cols).astype(np.int32)
    r0 = np.floor(rows).astype(np.int32)
    c1 = np.minimum(c0 + 1, source.shape[1] - 1)
    r1 = np.minimum(r0 + 1, source.shape[0] - 1)
    dc = cols - c0
    dr = rows - r0
    top = source[r0, c0] * (1.0 - dc) + source[r0, c1] * dc
    bottom = source[r1, c0] * (1.0 - dc) + source[r1, c1] * dc
    return top * (1.0 - dr) + bottom * dr


def terrarium_encode(elevations: np.ndarray) -> np.ndarray:
    quantized = np.rint((elevations + 32768.0) * 256.0).astype(np.int64)
    if quantized.min() < 0 or quantized.max() > 0xFFFFFF:
        raise ValueError("DEM elevation falls outside the Terrarium encoding range")
    return np.stack(
        ((quantized >> 16) & 255, (quantized >> 8) & 255, quantized & 255), axis=-1
    ).astype(np.uint8)


def terrarium_decode(rgb: np.ndarray) -> np.ndarray:
    values = rgb.astype(np.float64)
    return values[..., 0] * 256.0 + values[..., 1] + values[..., 2] / 256.0 - 32768.0


def generate(source_path: Path, output_dir: Path) -> dict:
    source_hash = sha256(source_path)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError(
            f"Unexpected source checksum: {source_hash}; expected {EXPECTED_SOURCE_SHA256}"
        )

    with rasterio.open(source_path) as dataset:
        if str(dataset.crs) != "EPSG:4326":
            raise ValueError(f"Expected EPSG:4326 source, found {dataset.crs}")
        source = dataset.read(1).astype(np.float64)
        nodata = dataset.nodata
        valid = np.isfinite(source) if nodata is None else np.isfinite(source) & (source != nodata)
        if not valid.all():
            raise ValueError("Source DEM contains nodata pixels inside its declared rectangular coverage")
        bounds = tuple(float(value) for value in dataset.bounds)
        transform = dataset.transform
        source_resolution = [abs(float(transform.a)), abs(float(transform.e))]
        source_shape = [dataset.height, dataset.width]
        source_min = float(source.min())
        source_max = float(source.max())

    output_dir.mkdir(parents=True, exist_ok=False)
    generated_tiles: list[Path] = []
    validation_errors: list[np.ndarray] = []
    boundary_transition_errors: list[np.ndarray] = []
    boundary_steps: list[np.ndarray] = []
    adjacent_steps: list[float] = []
    decoded_min = math.inf
    decoded_max = -math.inf
    coverage: dict[str, dict[str, int]] = {}

    for zoom in range(MIN_ZOOM, MAX_ZOOM + 1):
        x_min, x_max, y_min, y_max = tile_ranges(bounds, zoom)
        width = (x_max - x_min + 1) * TILE_SIZE
        height = (y_max - y_min + 1) * TILE_SIZE
        world_pixels = TILE_SIZE * (1 << zoom)

        # One shared padded Web Mercator pixel grid is sampled for the whole zoom.
        # Tiles are cropped from this common grid so adjacent edges cannot acquire
        # independent reprojection transforms or rounding differences.
        columns = np.arange(
            x_min * TILE_SIZE - EDGE_PADDING_PIXELS,
            (x_max + 1) * TILE_SIZE + EDGE_PADDING_PIXELS,
            dtype=np.float64,
        ) + 0.5
        rows = np.arange(
            y_min * TILE_SIZE - EDGE_PADDING_PIXELS,
            (y_max + 1) * TILE_SIZE + EDGE_PADDING_PIXELS,
            dtype=np.float64,
        ) + 0.5
        lons = columns / world_pixels * 360.0 - 180.0
        mercator = math.pi * (1.0 - 2.0 * rows / world_pixels)
        lats = np.degrees(np.arctan(np.sinh(mercator)))
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        elevations = sample_source(source, transform, lon_grid, lat_grid)

        core = elevations[
            EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + height,
            EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + width,
        ]
        encoded = terrarium_encode(core)
        decoded = terrarium_decode(encoded)
        decoded_min = min(decoded_min, float(decoded.min()))
        decoded_max = max(decoded_max, float(decoded.max()))
        if decoded.shape[1] > 1:
            adjacent_steps.append(float(np.abs(np.diff(decoded, axis=1)).max()))
        if decoded.shape[0] > 1:
            adjacent_steps.append(float(np.abs(np.diff(decoded, axis=0)).max()))

        # A tile edge must preserve the same adjacent-pixel transition as the
        # continuously sampled source grid. This catches shifted, duplicated,
        # or independently resampled edges rather than relying on visual review.
        for column in range(TILE_SIZE, width, TILE_SIZE):
            source_transition = core[:, column] - core[:, column - 1]
            decoded_transition = decoded[:, column] - decoded[:, column - 1]
            boundary_transition_errors.append(np.abs(decoded_transition - source_transition))
            boundary_steps.append(np.abs(decoded_transition))
        for row in range(TILE_SIZE, height, TILE_SIZE):
            source_transition = core[row, :] - core[row - 1, :]
            decoded_transition = decoded[row, :] - decoded[row - 1, :]
            boundary_transition_errors.append(np.abs(decoded_transition - source_transition))
            boundary_steps.append(np.abs(decoded_transition))

        inside = (
            (lon_grid[EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + height, EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + width] >= bounds[0])
            & (lon_grid[EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + height, EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + width] <= bounds[2])
            & (lat_grid[EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + height, EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + width] >= bounds[1])
            & (lat_grid[EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + height, EDGE_PADDING_PIXELS : EDGE_PADDING_PIXELS + width] <= bounds[3])
        )
        if inside.any():
            validation_errors.append(np.abs(decoded[inside] - core[inside]))

        for tile_y in range(y_min, y_max + 1):
            row = (tile_y - y_min) * TILE_SIZE
            for tile_x in range(x_min, x_max + 1):
                col = (tile_x - x_min) * TILE_SIZE
                tile = encoded[row : row + TILE_SIZE, col : col + TILE_SIZE]
                tile_path = output_dir / str(zoom) / str(tile_x) / f"{tile_y}.png"
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(tile, mode="RGB").save(
                    tile_path, format="PNG", optimize=False, compress_level=9
                )
                generated_tiles.append(tile_path)

        coverage[str(zoom)] = {
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "tile_count": (x_max - x_min + 1) * (y_max - y_min + 1),
        }

    errors = np.concatenate(validation_errors)
    seam_errors = np.concatenate(boundary_transition_errors)
    seam_steps = np.concatenate(boundary_steps)
    if float(errors.max()) > (1.0 / 256.0 + 1e-9):
        raise ValueError("Terrarium round-trip error exceeded one encoding unit")
    if float(seam_errors.max()) > (1.0 / 256.0 + 1e-9):
        raise ValueError("Terrarium encoding introduced a discontinuity at a tile boundary")
    if float(seam_steps.max()) > max(adjacent_steps) + 1e-9:
        raise ValueError("A tile boundary contains an elevation step larger than the terrain grid")
    if decoded_min < source_min - 1.0 or decoded_max > source_max + 1.0:
        raise ValueError("Encoded terrain introduced an extreme elevation outside the source range")

    tilejson = {
        "tilejson": "3.0.0",
        "name": "TerraSense Aizawl Copernicus GLO-30 terrain v1",
        "description": "Approximately 30 m Copernicus DEM terrain/DSM for the Aizawl detailed pilot; not live terrain or building-level elevation.",
        "version": "1.0.0",
        "scheme": "xyz",
        "tiles": ["/terrain/aizawl/v1/{z}/{x}/{y}.png"],
        "bounds": list(bounds),
        "minzoom": MIN_ZOOM,
        "maxzoom": MAX_ZOOM,
        "attribution": ATTRIBUTION,
    }
    tilejson_path = output_dir / "tiles.json"
    tilejson_path.write_text(json.dumps(tilejson, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    checksums = {
        path.relative_to(output_dir).as_posix(): sha256(path)
        for path in sorted([*generated_tiles, tilejson_path])
    }
    tile_bytes = sum(path.stat().st_size for path in generated_tiles)
    manifest = {
        "schema_version": 1,
        "terrain_version": "aizawl-v1",
        "source": {
            "filename": source_path.name,
            "sha256": source_hash,
            "product": "Copernicus DEM GLO-30 DSM",
            "crs": "EPSG:4326",
            "shape": source_shape,
            "resolution_degrees": source_resolution,
            "bounds": list(bounds),
            "nodata_value": nodata,
            "valid_elevation_range_m": [source_min, source_max],
        },
        "output": {
            "bounds": list(bounds),
            "encoding": "Terrarium",
            "encoding_formula": "height_m = R * 256 + G + B / 256 - 32768",
            "tile_scheme": "Web Mercator XYZ",
            "tile_size": TILE_SIZE,
            "minzoom": MIN_ZOOM,
            "maxzoom": MAX_ZOOM,
            "tile_count": len(generated_tiles),
            "total_compressed_tile_bytes": tile_bytes,
            "edge_padding_pixels": EDGE_PADDING_PIXELS,
            "edge_strategy": "sample each zoom on one shared Web Mercator grid with a one-pixel interpolation margin, then crop deterministic 256px tiles",
            "nodata_handling": "generation fails for source nodata; pixels outside the rectangular source bounds are edge-clamped and hidden by TileJSON bounds",
            "vertical_exaggeration": 1.0,
        },
        "validation": {
            "representative_pixel_count": int(errors.size),
            "average_round_trip_error_m": float(errors.mean()),
            "maximum_round_trip_error_m": float(errors.max()),
            "maximum_tile_boundary_transition_error_m": float(seam_errors.max()),
            "maximum_tile_boundary_elevation_step_m": float(seam_steps.max()),
            "maximum_adjacent_pixel_elevation_step_m": max(adjacent_steps),
            "decoded_elevation_range_m": [decoded_min, decoded_max],
            "all_tiles_intersect_declared_bounds": True,
            "source_nodata_pixel_count": 0,
        },
        "attribution": ATTRIBUTION,
        "zoom_coverage": coverage,
        "generated_file_sha256": checksums,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def tree_checksums(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="verify committed output without changing it")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()

    if not source.is_file():
        raise SystemExit(f"Source DEM is missing: {source}")
    if args.check and not output.is_dir():
        raise SystemExit(f"Terrain output is missing: {output}")
    if not args.check and output.exists():
        raise SystemExit(f"Refusing to replace existing output: {output}")

    with tempfile.TemporaryDirectory(prefix="terrasense-terrain-") as first_temp:
        first = Path(first_temp) / "v1"
        manifest = generate(source, first)
        expected = tree_checksums(first)
        if args.verify_determinism:
            with tempfile.TemporaryDirectory(prefix="terrasense-terrain-repeat-") as second_temp:
                second = Path(second_temp) / "v1"
                generate(source, second)
                if expected != tree_checksums(second):
                    raise SystemExit("Terrain output is not deterministic across two runs")
        if args.check:
            actual = tree_checksums(output)
            if expected != actual:
                raise SystemExit("Committed terrain output differs from deterministic generation")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(first, output)

    print(json.dumps({
        "status": "READY",
        "source_sha256": manifest["source"]["sha256"],
        "tile_count": manifest["output"]["tile_count"],
        "tile_bytes": manifest["output"]["total_compressed_tile_bytes"],
        "average_error_m": manifest["validation"]["average_round_trip_error_m"],
        "maximum_error_m": manifest["validation"]["maximum_round_trip_error_m"],
        "deterministic": bool(args.verify_determinism or args.check),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
