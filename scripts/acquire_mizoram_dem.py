"""Plan and, only with two explicit flags, acquire Copernicus GLO-30 tiles.

The default command performs metadata-only HEAD requests and writes a
deterministic plan manifest. It never downloads raster content.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import rasterio
from rasterio.transform import Affine, array_bounds
from rasterio.windows import Window
from shapely.geometry import box, shape


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOUNDARY = REPO_ROOT / "data" / "geodata" / "ner" / "states.geojson"
DEFAULT_PLAN_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "manifests"
    / "susceptibility"
    / "copernicus_glo30_2021_plan.json"
)
DEFAULT_RAW_DIR = (
    REPO_ROOT
    / "local-data"
    / "susceptibility"
    / "copernicus-glo30-2021"
    / "raw"
)
DEFAULT_ACQUISITION_MANIFEST = DEFAULT_RAW_DIR.parent / "acquisition_manifest.json"

PRODUCT = "Copernicus DEM GLO-30 Public"
PRODUCT_IDENTIFIER = "COP-DEM_GLO-30-DGED"
PRODUCT_RELEASE = "2021 AWS public release"
SOURCE_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
TRUSTED_SOURCE_HOST = "copernicus-dem-30m.s3.amazonaws.com"
REGISTRY_URL = "https://registry.opendata.aws/copernicus-dem/"
PRODUCT_HANDBOOK_URL = (
    "https://dataspace.copernicus.eu/sites/default/files/media/files/2024-06/"
    "geo1988-copernicusdem-spe-002_producthandbook_i5.0.pdf"
)
LICENCE_URL = (
    "https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/"
    "resources/license/License-COPDEM-30.pdf"
)
SOURCE_ATTRIBUTION = (
    "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA; all rights reserved."
)
DERIVATIVE_ATTRIBUTION = (
    "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and "
    "© Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS "
    "by the European Union and ESA; all rights reserved"
)
LIABILITY_NOTICE = (
    "The organisations in charge of the Copernicus programme by law or by "
    "delegation do not incur any liability for any use of the Copernicus WorldDEM-30"
)
LICENCE_ACCEPTED_BY = "TerraSense project owner"
LICENCE_ACCEPTED_ON = "2026-09-26"
BOUNDARY_STATE_ID = "IN-MZ"
BOUNDARY_VERSION = "geoBoundaries gbOpen India ADM1; release 9469f09; 2011 boundary vintage"
HTTP_TIMEOUT_SECONDS = 20
MAX_DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
REQUIRED_DISK_RESERVE_BYTES = 2 * 1024**3
EXPECTED_RASTER_DIMENSION = 3600
EXPECTED_GRID_SEMANTICS = "Point"
AFFINE_ABS_TOLERANCE = 1e-12
TILE_IDENTIFIER_PATTERN = re.compile(
    r"^Copernicus_DSM_COG_10_[NS](?:[0-8]\d|90)_00_"
    r"[EW](?:[01]\d\d|180)_00_DEM$"
)


class AcquisitionError(RuntimeError):
    """Raised when source metadata or a guarded acquisition fails validation."""


class RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so an approved S3 URL cannot escape its trusted origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionError(f"Refusing redirect from {req.full_url} to {newurl}")


TRUSTED_OPENER = urllib.request.build_opener(RejectRedirectHandler())


@dataclass(frozen=True)
class TilePlan:
    tile_id: str
    bounds: tuple[int, int, int, int]
    url: str


@dataclass(frozen=True)
class RemoteMetadata:
    content_length: int
    etag: str | None
    last_modified: str | None
    content_type: str | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_file_or_none(path: Path) -> str | None:
    return sha256_file(path) if path.is_file() else None


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def load_mizoram_geometry(boundary_path: Path = DEFAULT_BOUNDARY):
    document = json.loads(boundary_path.read_text(encoding="utf-8"))
    if document.get("type") != "FeatureCollection":
        raise AcquisitionError(f"{boundary_path} is not a GeoJSON FeatureCollection")
    matches = [
        feature
        for feature in document.get("features", [])
        if feature.get("properties", {}).get("state_id") == BOUNDARY_STATE_ID
    ]
    if len(matches) != 1:
        raise AcquisitionError(
            f"Expected one {BOUNDARY_STATE_ID} boundary in {boundary_path}, found {len(matches)}"
        )
    geometry = shape(matches[0].get("geometry"))
    if geometry.is_empty or not geometry.is_valid:
        raise AcquisitionError("The canonical Mizoram boundary is empty or invalid")
    return geometry


def coordinate_token(value: int, positive: str, negative: str, width: int) -> str:
    hemisphere = positive if value >= 0 else negative
    return f"{hemisphere}{abs(value):0{width}d}_00"


def tile_identifier(west: int, south: int) -> str:
    northing = coordinate_token(south, "N", "S", 2)
    easting = coordinate_token(west, "E", "W", 3)
    return f"Copernicus_DSM_COG_10_{northing}_{easting}_DEM"


def validate_source_url(url: str, tile_id: str | None = None) -> str:
    """Return the validated tile identifier for an exact public-bucket URL."""
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise AcquisitionError(f"Malformed Copernicus source URL: {url}") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != TRUSTED_SOURCE_HOST
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise AcquisitionError(f"Untrusted Copernicus source URL: {url}")
    if urllib.parse.unquote(parsed.path) != parsed.path:
        raise AcquisitionError(f"Encoded source paths are not allowed: {url}")
    parts = parsed.path.split("/")
    if len(parts) != 3 or parts[0] != "" or not TILE_IDENTIFIER_PATTERN.fullmatch(parts[1]):
        raise AcquisitionError(f"Invalid Copernicus tile path: {url}")
    identifier = parts[1]
    if tile_id is not None and identifier != tile_id:
        raise AcquisitionError(f"Source URL does not match tile identifier {tile_id}")
    if parts[2] != f"{identifier}.tif":
        raise AcquisitionError(f"Source URL does not name the expected GeoTIFF: {url}")
    return identifier


def validate_content_range(value: str | None, offset: int, expected_size: int) -> None:
    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", value or "")
    if match is None:
        raise AcquisitionError(f"Resume response has invalid Content-Range {value!r}")
    start, end, total = (int(part) for part in match.groups())
    if start != offset or total != expected_size or end < start or end >= total:
        raise AcquisitionError(
            f"Resume response Content-Range {value!r} does not match "
            f"offset {offset} and expected size {expected_size}"
        )


def open_trusted_request(request: urllib.request.Request, timeout: int):
    validate_source_url(request.full_url)
    return TRUSTED_OPENER.open(request, timeout=timeout)


def derive_tile_plan(geometry) -> list[TilePlan]:
    minx, miny, maxx, maxy = geometry.bounds
    plans: list[TilePlan] = []
    for south in range(math.floor(miny), math.ceil(maxy)):
        for west in range(math.floor(minx), math.ceil(maxx)):
            bounds = (west, south, west + 1, south + 1)
            # Positive-area intersection avoids including a cell touched only at an edge.
            if geometry.intersection(box(*bounds)).area <= 0:
                continue
            identifier = tile_identifier(west, south)
            url = f"{SOURCE_BASE_URL}/{identifier}/{identifier}.tif"
            plans.append(TilePlan(identifier, bounds, url))
    return sorted(plans, key=lambda item: item.tile_id)


def _first_header(headers: Any, name: str) -> str | None:
    value = headers.get(name)
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else None
    return str(value)


def probe_remote_metadata(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> RemoteMetadata:
    validate_source_url(url)
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "TerraSense-Phase5B0/1.0"},
    )
    try:
        with open_trusted_request(request, timeout) as response:
            status = getattr(response, "status", response.getcode())
            if status != 200:
                raise AcquisitionError(f"HEAD {url} returned HTTP {status}")
            length_text = _first_header(response.headers, "Content-Length")
            if not length_text or int(length_text) <= 0:
                raise AcquisitionError(f"HEAD {url} did not return a positive Content-Length")
            return RemoteMetadata(
                content_length=int(length_text),
                etag=_first_header(response.headers, "ETag"),
                last_modified=_first_header(response.headers, "Last-Modified"),
                content_type=_first_header(response.headers, "Content-Type"),
            )
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        raise AcquisitionError(f"Metadata request failed for {url}: {exc}") from exc


def _boundary_metadata(boundary_path: Path, geometry) -> dict[str, Any]:
    return {
        "canonical_path": "data/geodata/ner/states.geojson",
        "state_id": BOUNDARY_STATE_ID,
        "source_version": BOUNDARY_VERSION,
        "crs": "EPSG:4326",
        "sha256": sha256_file(boundary_path),
        "bounds": [round(value, 12) for value in geometry.bounds],
    }


def build_plan_manifest(
    boundary_path: Path = DEFAULT_BOUNDARY,
    metadata_fetcher: Callable[[str], RemoteMetadata] = probe_remote_metadata,
) -> dict[str, Any]:
    geometry = load_mizoram_geometry(boundary_path)
    plans = derive_tile_plan(geometry)
    tiles: list[dict[str, Any]] = []
    for plan in plans:
        remote = metadata_fetcher(plan.url)
        tiles.append(
            {
                "tile_id": plan.tile_id,
                "url": plan.url,
                "bounds_epsg4326": list(plan.bounds),
                "expected_size_bytes": remote.content_length,
                "provider_object_etag": remote.etag,
                "provider_last_modified": remote.last_modified,
                "content_type": remote.content_type,
                "provider_checksum": None,
                "local_sha256": None,
            }
        )
    total = sum(tile["expected_size_bytes"] for tile in tiles)
    return {
        "schema_version": 1,
        "status": "PLAN_ONLY_NO_RASTER_DOWNLOAD",
        "raster_bytes_downloaded": 0,
        "boundary": _boundary_metadata(boundary_path, geometry),
        "source": {
            "product": PRODUCT,
            "product_identifier": PRODUCT_IDENTIFIER,
            "release": PRODUCT_RELEASE,
            "distribution": "AWS Registry of Open Data / Sinergise COG conversion",
            "base_url": SOURCE_BASE_URL,
            "registry_url": REGISTRY_URL,
            "product_handbook_url": PRODUCT_HANDBOOK_URL,
            "credentials_required": False,
            "native_horizontal_crs": "EPSG:4326",
            "vertical_datum": "EGM2008 (EPSG:3855)",
            "native_spacing": "1 arc-second latitude; longitude spacing per DGED latitude band",
        },
        "licence": {
            "name": "Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free & Open",
            "url": LICENCE_URL,
            "accepted_by": LICENCE_ACCEPTED_BY,
            "accepted_on": LICENCE_ACCEPTED_ON,
            "accepted_for_project": "TerraSense",
            "source_attribution": SOURCE_ATTRIBUTION,
            "derivative_attribution": DERIVATIVE_ATTRIBUTION,
            "liability_notice": LIABILITY_NOTICE,
            "non_endorsement_required": True,
            "downstream_users_must_receive_applicable_obligations": True,
            "raw_redistribution": "permitted with source and liability notices and downstream obligations",
            "derived_redistribution": "permitted with derivative attribution, liability notice, and downstream obligations",
        },
        "storage": {
            "raw_directory": "local-data/susceptibility/copernicus-glo30-2021/raw",
            "required_disk_reserve_bytes": REQUIRED_DISK_RESERVE_BYTES,
        },
        "tile_count": len(tiles),
        "total_expected_size_bytes": total,
        "tiles": tiles,
    }


def manifest_changes(
    previous: dict[str, Any] | None, current: dict[str, Any]
) -> list[str]:
    if previous is None:
        return []
    old_tiles = {tile["tile_id"]: tile for tile in previous.get("tiles", [])}
    messages: list[str] = []
    for tile in current["tiles"]:
        old = old_tiles.get(tile["tile_id"])
        if old is None:
            messages.append(f"new tile: {tile['tile_id']}")
            continue
        for field in ("expected_size_bytes", "provider_object_etag", "provider_last_modified"):
            if old.get(field) != tile.get(field):
                messages.append(
                    f"{tile['tile_id']} {field}: {old.get(field)!r} -> {tile.get(field)!r}"
                )
    removed = sorted(set(old_tiles) - {tile["tile_id"] for tile in current["tiles"]})
    messages.extend(f"removed tile: {tile_id}" for tile_id in removed)
    return messages


def has_tiff_signature(prefix: bytes) -> bool:
    return prefix[:4] in {b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"}


def validate_response_type(content_type: str | None, prefix: bytes) -> None:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized in {"text/html", "text/xml", "application/xml", "application/json"}:
        raise AcquisitionError(f"Remote response is {normalized}, not a GeoTIFF")
    if not has_tiff_signature(prefix):
        raise AcquisitionError("Remote response does not begin with a TIFF signature")


def expected_point_grid_transform(
    nominal_bounds: Iterable[float],
    width: int,
    height: int,
) -> Affine:
    """Return GDAL's area-oriented affine for a point-posted geographic grid.

    Copernicus DGED coordinates identify sample centres. GDAL's affine transform
    identifies pixel corners, so the outer affine footprint begins half a sample
    west and north of the nominal northwest point.
    """
    bounds = tuple(float(value) for value in nominal_bounds)
    if len(bounds) != 4:
        raise AcquisitionError(f"Expected four nominal bounds, received {bounds}")
    west, south, east, north = bounds
    if width <= 0 or height <= 0 or east <= west or north <= south:
        raise AcquisitionError(
            f"Invalid point-grid dimensions or nominal bounds: {width}x{height}, {bounds}"
        )
    pixel_width = (east - west) / width
    pixel_height = (north - south) / height
    return Affine(
        pixel_width,
        0.0,
        west - pixel_width / 2.0,
        0.0,
        -pixel_height,
        north + pixel_height / 2.0,
    )


def _affine_value_matches(actual: float, expected: float) -> bool:
    return math.isclose(
        actual,
        expected,
        rel_tol=0.0,
        abs_tol=AFFINE_ABS_TOLERANCE,
    )


def validate_dem_tile(
    path: Path,
    expected_bounds: Iterable[float],
    *,
    expected_dimension: int = EXPECTED_RASTER_DIMENSION,
) -> dict[str, Any]:
    with path.open("rb") as stream:
        validate_response_type(None, stream.read(4))
    bounds = tuple(float(value) for value in expected_bounds)
    expected_transform = expected_point_grid_transform(
        bounds,
        expected_dimension,
        expected_dimension,
    )
    try:
        with rasterio.open(path) as dataset:
            if dataset.count != 1:
                raise AcquisitionError(f"{path.name} has {dataset.count} bands; expected one")
            if dataset.crs is None or dataset.crs.to_epsg() != 4326:
                raise AcquisitionError(f"{path.name} CRS is {dataset.crs}; expected EPSG:4326")
            if dataset.width != expected_dimension or dataset.height != expected_dimension:
                raise AcquisitionError(
                    f"{path.name} is {dataset.width}x{dataset.height}; "
                    f"expected {expected_dimension}x{expected_dimension}"
                )
            if dataset.dtypes[0] != "float32":
                raise AcquisitionError(f"{path.name} dtype is {dataset.dtypes[0]}; expected float32")
            if dataset.nodata not in (None, -32767.0):
                raise AcquisitionError(
                    f"{path.name} nodata is {dataset.nodata}; expected unset or -32767"
                )

            grid_semantics = dataset.tags().get("AREA_OR_POINT")
            if grid_semantics != EXPECTED_GRID_SEMANTICS:
                rendered = repr(grid_semantics) if grid_semantics is not None else "missing"
                raise AcquisitionError(
                    f"{path.name} AREA_OR_POINT is {rendered}; expected explicit "
                    f"{EXPECTED_GRID_SEMANTICS!r} for Copernicus GLO-30 DGED"
                )

            transform = dataset.transform
            if not _affine_value_matches(transform.b, 0.0) or not _affine_value_matches(
                transform.d, 0.0
            ):
                raise AcquisitionError(
                    f"{path.name} transform has rotation or shear: {transform}"
                )
            if not _affine_value_matches(
                transform.a, expected_transform.a
            ) or not _affine_value_matches(transform.e, expected_transform.e):
                raise AcquisitionError(
                    f"{path.name} resolution is ({transform.a}, {abs(transform.e)}); "
                    f"expected ({expected_transform.a}, {abs(expected_transform.e)})"
                )
            if not _affine_value_matches(
                transform.c, expected_transform.c
            ) or not _affine_value_matches(transform.f, expected_transform.f):
                raise AcquisitionError(
                    f"{path.name} point-grid origin is ({transform.c}, {transform.f}); "
                    f"expected ({expected_transform.c}, {expected_transform.f}) from "
                    f"nominal bounds {bounds}"
                )

            actual_bounds = tuple(dataset.bounds)
            expected_affine_bounds = tuple(
                array_bounds(expected_dimension, expected_dimension, expected_transform)
            )
            if any(
                not _affine_value_matches(actual, expected)
                for actual, expected in zip(actual_bounds, expected_affine_bounds)
            ):
                raise AcquisitionError(
                    f"{path.name} affine bounds are {actual_bounds}; expected "
                    f"{expected_affine_bounds} for nominal tile bounds {bounds}"
                )
            dataset.read(1, window=Window(0, 0, 1, 1))
            return {
                "width": dataset.width,
                "height": dataset.height,
                "crs": dataset.crs.to_string(),
                "dtype": dataset.dtypes[0],
                "bounds": list(actual_bounds),
                "nominal_bounds": list(bounds),
                "transform": list(transform)[:6],
                "resolution": [transform.a, abs(transform.e)],
                "grid_semantics": grid_semantics,
                "nodata": dataset.nodata,
            }
    except rasterio.errors.RasterioIOError as exc:
        raise AcquisitionError(f"Rasterio cannot read {path}: {exc}") from exc


def validate_existing_file(
    path: Path,
    tile: dict[str, Any],
    previous_sha256: str | None = None,
    *,
    expected_dimension: int = EXPECTED_RASTER_DIMENSION,
) -> str:
    actual_size = path.stat().st_size
    if actual_size != tile["expected_size_bytes"]:
        raise AcquisitionError(
            f"Refusing to overwrite {path}: size {actual_size} differs from "
            f"expected {tile['expected_size_bytes']}"
        )
    actual_sha256 = sha256_file(path)
    if previous_sha256 and actual_sha256 != previous_sha256:
        raise AcquisitionError(
            f"Refusing to overwrite {path}: SHA-256 differs from the acquisition manifest"
        )
    validate_dem_tile(
        path,
        tile["bounds_epsg4326"],
        expected_dimension=expected_dimension,
    )
    return actual_sha256


def _load_local_sha256(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.is_file():
        return {}
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        tile["tile_id"]: tile["local_sha256"]
        for tile in document.get("tiles", [])
        if tile.get("local_sha256")
    }


def _download_one(tile: dict[str, Any], destination: Path, timeout: int) -> None:
    validate_source_url(tile["url"], tile["tile_id"])
    partial = destination.with_suffix(destination.suffix + ".part")
    expected_size = tile["expected_size_bytes"]
    for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > expected_size:
            raise AcquisitionError(f"Partial file exceeds expected size: {partial}")
        if offset:
            with partial.open("rb") as stream:
                validate_response_type(None, stream.read(4))
        if offset == expected_size:
            validate_dem_tile(partial, tile["bounds_epsg4326"])
            os.replace(partial, destination)
            return
        headers = {"User-Agent": "TerraSense-Phase5B0/1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(tile["url"], headers=headers)
        try:
            with open_trusted_request(request, timeout) as response:
                status = getattr(response, "status", response.getcode())
                if not offset and status != 200:
                    raise AcquisitionError(
                        f"Initial download for {tile['tile_id']} returned HTTP {status}"
                    )
                if offset and status != 206:
                    offset = 0
                mode = "ab" if offset and status == 206 else "wb"
                first = response.read(4)
                content_type = _first_header(response.headers, "Content-Type")
                if offset and status == 206:
                    content_range = _first_header(response.headers, "Content-Range")
                    validate_content_range(content_range, offset, expected_size)
                    normalized = (content_type or "").split(";", 1)[0].strip().lower()
                    if normalized in {"text/html", "text/xml", "application/xml", "application/json"}:
                        raise AcquisitionError(f"Remote response is {normalized}, not a GeoTIFF")
                else:
                    validate_response_type(content_type, first)
                with partial.open(mode) as stream:
                    stream.write(first)
                    while block := response.read(DOWNLOAD_CHUNK_BYTES):
                        stream.write(block)
            if partial.stat().st_size != expected_size:
                raise AcquisitionError(
                    f"Downloaded size for {tile['tile_id']} is {partial.stat().st_size}; "
                    f"expected {expected_size}"
                )
            validate_dem_tile(partial, tile["bounds_epsg4326"])
            os.replace(partial, destination)
            return
        except (TimeoutError, urllib.error.URLError, OSError, AcquisitionError) as exc:
            if attempt == MAX_DOWNLOAD_ATTEMPTS:
                raise AcquisitionError(
                    f"Download failed for {tile['tile_id']} after {attempt} attempts: {exc}"
                ) from exc
            time.sleep(min(2 ** (attempt - 1), 4))


def acquire_tiles(
    plan: dict[str, Any],
    raw_dir: Path,
    acquisition_manifest_path: Path,
    timeout: int = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    licence = plan.get("licence", {})
    if not licence.get("accepted_by") or not licence.get("accepted_on"):
        raise AcquisitionError("Copernicus licence acceptance is not recorded")
    required_free = (
        int(plan["total_expected_size_bytes"])
        + int(plan["storage"]["required_disk_reserve_bytes"])
    )
    disk_probe = raw_dir.resolve()
    while not disk_probe.exists() and disk_probe.parent != disk_probe:
        disk_probe = disk_probe.parent
    available = shutil.disk_usage(disk_probe).free
    if available < required_free:
        raise AcquisitionError(
            f"Insufficient disk space: {available} bytes free; "
            f"at least {required_free} bytes are required"
        )
    raw_dir.mkdir(parents=True, exist_ok=True)
    previous_hashes = _load_local_sha256(acquisition_manifest_path)
    acquired: list[dict[str, Any]] = []
    for tile in plan["tiles"]:
        validate_source_url(tile["url"], tile["tile_id"])
        destination = raw_dir / f"{tile['tile_id']}.tif"
        if destination.exists():
            local_hash = validate_existing_file(
                destination,
                tile,
                previous_hashes.get(tile["tile_id"]),
            )
            retrieved_at = None
            status = "REUSED_VALIDATED"
        else:
            _download_one(tile, destination, timeout)
            local_hash = sha256_file(destination)
            retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
            status = "DOWNLOADED"
        acquired.append(
            {
                **tile,
                "local_sha256": local_hash,
                "retrieved_at_utc": retrieved_at,
                "status": status,
            }
        )
    result = {
        **plan,
        "status": "ACQUIRED_AND_VALIDATED",
        "tiles": acquired,
    }
    atomic_write_json(acquisition_manifest_path, result)
    return result


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run(
    *,
    boundary: Path,
    plan_manifest: Path,
    raw_dir: Path,
    acquisition_manifest: Path,
    download: bool,
    confirm_download: bool,
    timeout: int,
) -> dict[str, Any]:
    previous = _read_json_if_present(plan_manifest)
    plan = build_plan_manifest(
        boundary,
        metadata_fetcher=lambda url: probe_remote_metadata(url, timeout=timeout),
    )
    changes = manifest_changes(previous, plan)
    atomic_write_json(plan_manifest, plan)
    if download != confirm_download:
        raise AcquisitionError(
            "A real download requires both --download and --confirm-download; neither flag alone is valid"
        )
    if download:
        result = acquire_tiles(plan, raw_dir, acquisition_manifest, timeout)
    else:
        result = plan
    result = {**result, "remote_metadata_changes": changes, "raster_bytes_downloaded": 0 if not download else None}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundary", type=Path, default=DEFAULT_BOUNDARY)
    parser.add_argument("--plan-manifest", type=Path, default=DEFAULT_PLAN_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument(
        "--acquisition-manifest", type=Path, default=DEFAULT_ACQUISITION_MANIFEST
    )
    parser.add_argument("--timeout", type=int, default=HTTP_TIMEOUT_SECONDS)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--confirm-download", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(
            boundary=args.boundary.resolve(),
            plan_manifest=args.plan_manifest.resolve(),
            raw_dir=args.raw_dir.resolve(),
            acquisition_manifest=args.acquisition_manifest.resolve(),
            download=args.download,
            confirm_download=args.confirm_download,
            timeout=args.timeout,
        )
    except AcquisitionError as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": result["status"],
                "tile_count": result["tile_count"],
                "tile_ids": [tile["tile_id"] for tile in result["tiles"]],
                "total_expected_size_bytes": result["total_expected_size_bytes"],
                "required_disk_reserve_bytes": result["storage"]["required_disk_reserve_bytes"],
                "raster_bytes_downloaded": result["raster_bytes_downloaded"],
                "remote_metadata_changes": result["remote_metadata_changes"],
                "plan_manifest": display_path(args.plan_manifest),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
