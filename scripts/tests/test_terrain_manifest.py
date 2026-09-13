import hashlib
import json
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERRAIN_DIR = REPO_ROOT / "frontend" / "public" / "terrain" / "aizawl" / "v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decode_png_rgb(path: Path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    compressed = bytearray()
    width = height = color_type = bit_depth = None
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", payload[:10])
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    assert (width, height, bit_depth, color_type) == (256, 256, 8, 2)
    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    rows = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for index, value in enumerate(scanline):
            left = scanline[index - 3] if index >= 3 else 0
            above = previous[index]
            upper_left = previous[index - 3] if index >= 3 else 0
            if filter_type == 1:
                scanline[index] = (value + left) & 255
            elif filter_type == 2:
                scanline[index] = (value + above) & 255
            elif filter_type == 3:
                scanline[index] = (value + ((left + above) // 2)) & 255
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = left if distances[0] <= distances[1] and distances[0] <= distances[2] else above if distances[1] <= distances[2] else upper_left
                scanline[index] = (value + predictor) & 255
            else:
                assert filter_type == 0
        rows.append(scanline)
        previous = scanline
    return rows


def test_aizawl_terrain_manifest_and_generated_files_are_complete():
    manifest = json.loads((TERRAIN_DIR / "manifest.json").read_text(encoding="utf-8"))
    output = manifest["output"]
    assert manifest["source"]["sha256"] == "dcbfe1a282feade4c77bfbf0717bae7126a63eca31524fae1e61a974a7924ed9"
    assert manifest["source"]["crs"] == "EPSG:4326"
    assert output["encoding"] == "Terrarium"
    assert output["tile_scheme"] == "Web Mercator XYZ"
    assert output["tile_size"] == 256
    assert (output["minzoom"], output["maxzoom"]) == (8, 13)
    assert output["tile_count"] == 21
    assert output["vertical_exaggeration"] == 1.0
    assert output["total_compressed_tile_bytes"] < 15 * 1024 * 1024
    assert manifest["validation"]["source_nodata_pixel_count"] == 0
    assert manifest["validation"]["maximum_round_trip_error_m"] <= 1 / 256
    assert manifest["validation"]["maximum_tile_boundary_transition_error_m"] <= 1 / 256
    assert (
        manifest["validation"]["maximum_tile_boundary_elevation_step_m"]
        <= manifest["validation"]["maximum_adjacent_pixel_elevation_step_m"]
    )

    checksums = manifest["generated_file_sha256"]
    assert len([name for name in checksums if name.endswith(".png")]) == output["tile_count"]
    for name, expected in checksums.items():
        assert _sha256(TERRAIN_DIR / name) == expected

    tiles = json.loads((TERRAIN_DIR / "tiles.json").read_text(encoding="utf-8"))
    assert tiles["tiles"] == ["/terrain/aizawl/v1/{z}/{x}/{y}.png"]
    assert tiles["bounds"] == manifest["output"]["bounds"]
    assert "COPERNICUS" in tiles["attribution"].upper()


def test_terrarium_tiles_decode_without_extreme_peaks_or_pits():
    manifest = json.loads((TERRAIN_DIR / "manifest.json").read_text(encoding="utf-8"))
    source_min, source_max = manifest["source"]["valid_elevation_range_m"]
    decoded = []
    for relative in manifest["generated_file_sha256"]:
        if not relative.endswith(".png"):
            continue
        for row in _decode_png_rgb(TERRAIN_DIR / relative):
            for index in range(0, len(row), 3):
                decoded.append(row[index] * 256 + row[index + 1] + row[index + 2] / 256 - 32768)
    assert min(decoded) >= source_min - 1
    assert max(decoded) <= source_max + 1


def test_every_generated_tile_is_in_the_declared_zoom_coverage():
    manifest = json.loads((TERRAIN_DIR / "manifest.json").read_text(encoding="utf-8"))
    coverage = manifest["zoom_coverage"]
    pngs = list(TERRAIN_DIR.glob("*/*/*.png"))
    assert len(pngs) == manifest["output"]["tile_count"]
    for path in pngs:
        zoom, tile_x, tile_y = int(path.parts[-3]), int(path.parts[-2]), int(path.stem)
        limits = coverage[str(zoom)]
        assert limits["x_min"] <= tile_x <= limits["x_max"]
        assert limits["y_min"] <= tile_y <= limits["y_max"]
