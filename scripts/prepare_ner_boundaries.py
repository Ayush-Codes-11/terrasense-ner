"""Prepare Northeast India state and district GeoJSON files.

Source metadata:
  ADM1: geoBoundaries gbOpen/IND/ADM1, release commit 9469f09
  ADM2: geoBoundaries gbOpen/IND/ADM2, release commit 9469f09

The source files are downloaded on demand and intentionally are not committed.
Requires: shapely (2.x).
"""

from __future__ import annotations

import argparse
import json
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "geodata" / "ner"
ADM1_PATH = OUTPUT_DIR / "_source_adm1.geojson"
ADM2_PATH = OUTPUT_DIR / "_source_adm2.geojson"

ADM1_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/"
    "releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1.geojson"
)
ADM2_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/"
    "releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson"
)

STATES = {
    "IN-AR": "Arunachal Pradesh",
    "IN-AS": "Assam",
    "IN-MN": "Manipur",
    "IN-ML": "Meghalaya",
    "IN-MZ": "Mizoram",
    "IN-NL": "Nagaland",
    "IN-SK": "Sikkim",
    "IN-TR": "Tripura",
}

def download_if_missing(url: str, path: Path, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, path)


def read_geojson(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if document.get("type") != "FeatureCollection":
        raise ValueError(f"{path} is not a FeatureCollection")
    return document


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return document


def feature_properties(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("Source feature has no properties object")
    return properties


def normalize_state_name(name: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", name)
        if not unicodedata.combining(character)
    )


def write_geojson(path: Path, features: list[dict[str, Any]]) -> None:
    document = {
        "type": "FeatureCollection",
        "name": path.stem,
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
    }
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def validate(features: list[dict[str, Any]], id_key: str) -> None:
    ids = [feature["properties"][id_key] for feature in features]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {id_key} values")
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            raise ValueError(f"Null geometry for {feature['properties'][id_key]}")
        geom = shape(geometry)
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Invalid geometry for {feature['properties'][id_key]}")
        if geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"Unexpected geometry type {geom.geom_type}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    download_if_missing(ADM1_URL, ADM1_PATH, args.force_download)
    download_if_missing(ADM2_URL, ADM2_PATH, args.force_download)
    adm1 = read_geojson(ADM1_PATH)
    adm2 = read_geojson(ADM2_PATH)

    state_features: list[dict[str, Any]] = []
    state_geometries: dict[str, Any] = {}
    for source_feature in adm1["features"]:
        source = feature_properties(source_feature)
        state_id = source.get("shapeISO")
        if state_id not in STATES:
            continue
        state_name = normalize_state_name(source.get("shapeName"))
        if state_name != STATES[state_id]:
            raise ValueError(f"Unexpected state name for {state_id}: {source.get('shapeName')}")
        feature = {
            "type": "Feature",
            "geometry": source_feature["geometry"],
            "properties": {
                "state_id": state_id,
                "state_name": state_name,
                "region_id": "NER",
                "admin_level": "state",
                "source_feature_id": source["shapeID"],
                "source": "geoBoundaries gbOpen India ADM1",
                "source_version": "2011 boundary vintage; build 2023-12-12",
            },
        }
        state_features.append(feature)
        state_geometries[state_id] = shape(feature["geometry"])

    if set(state_geometries) != set(STATES):
        raise ValueError(f"Expected all 8 states, got {sorted(state_geometries)}")

    district_features: list[dict[str, Any]] = []
    for source_feature in adm2["features"]:
        source = feature_properties(source_feature)
        geometry = shape(source_feature["geometry"])
        representative = geometry.representative_point()
        state_id = next(
            (candidate for candidate, state_geometry in state_geometries.items()
             if state_geometry.covers(representative)),
            None,
        )
        if state_id is None:
            continue
        district_name = source.get("shapeName")
        if not district_name:
            raise ValueError(f"Missing district name for {source['shapeID']}")
        district_features.append(
            {
                "type": "Feature",
                "geometry": source_feature["geometry"],
                "properties": {
                    "district_id": f"IND-ADM2-{source['shapeID']}",
                    "district_name": district_name,
                    "state_id": state_id,
                    "lgd_code": None,
                    "source_feature_id": source["shapeID"],
                    "admin_level": "district",
                    "source": "geoBoundaries gbOpen India ADM2",
                    "source_version": "2021 boundary vintage; build 2023-12-12",
                },
            }
        )

    state_features.sort(key=lambda feature: feature["properties"]["state_id"])
    district_features.sort(
        key=lambda feature: (
            feature["properties"]["state_id"],
            feature["properties"]["district_name"],
        )
    )
    validate(state_features, "state_id")
    validate(district_features, "district_id")
    if any(feature["properties"]["state_id"] not in STATES for feature in district_features):
        raise ValueError("District linked to an unknown state")

    ner_geometry = unary_union([shape(feature["geometry"]) for feature in state_features])
    ner_feature = {
        "type": "Feature",
        "geometry": ner_geometry.__geo_interface__,
        "properties": {
            "region_id": "NER",
            "region_name": "Northeast Region",
            "admin_level": "region",
            "source": "Dissolved from validated NER state boundaries",
            "source_version": "geoBoundaries release 9469f09",
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_geojson(OUTPUT_DIR / "states.geojson", state_features)
    write_geojson(OUTPUT_DIR / "districts.geojson", district_features)
    write_geojson(OUTPUT_DIR / "ner_boundary.geojson", [ner_feature])

    counts = {
        state_id: sum(
            feature["properties"]["state_id"] == state_id
            for feature in district_features
        )
        for state_id in STATES
    }
    aizawl_matches = [
        feature
        for feature in district_features
        if feature["properties"]["district_name"] == "Aizawl"
        and feature["properties"]["state_id"] == "IN-MZ"
    ]
    if len(aizawl_matches) != 1:
        raise ValueError(
            "Expected exactly one Aizawl district under IN-MZ, "
            f"found {len(aizawl_matches)}"
        )
    aizawl = aizawl_matches[0]
    metadata_path = OUTPUT_DIR / "metadata.json"
    existing_metadata: dict[str, Any] = {}
    if metadata_path.exists():
        existing_metadata = read_json(metadata_path)
    metadata = {
        "regions": [{"region_id": "NER", "region_name": "Northeast Region"}],
        "pilot_district_id": aizawl["properties"]["district_id"],
        "dataset_source": {
            "adm1_states": {
                "name": "geoBoundaries gbOpen India ADM1",
                "release": "9469f09",
                "boundary_vintage": "2011",
                "upstream_sources": [
                    "DataMeet India community",
                    "Election Commission of India",
                ],
                "license": "CC BY 2.5 India",
            },
            "adm2_districts": {
                "name": "geoBoundaries gbOpen India ADM2",
                "release": "9469f09",
                "boundary_vintage": "2021",
                "upstream_sources": [
                    "Pathways Data Pvt. Ltd.",
                    "lgdirectory.gov.in",
                ],
                "license": "ODbL 1.0",
            },
        },
        "dataset_version": "ADM1 2011 / ADM2 2021 boundary vintages; built 2023-12-12",
        "crs": "EPSG:4326",
        "state_count": len(state_features),
        "district_count": len(district_features),
        "district_count_by_state": counts,
        "lgd_mapping_status": "Not provided by geometry features; no LGD codes guessed",
        "administrative_list_comparison_date": existing_metadata.get(
            "administrative_list_comparison_date"
        ),
        "administrative_list_comparison_status": existing_metadata.get(
            "administrative_list_comparison_status",
            "Not recorded; current LGD comparison has not been attempted",
        ),
        "generated_on": date.today().isoformat(),
    }
    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(json.dumps({
        "states": len(state_features),
        "districts": len(district_features),
        "district_count_by_state": counts,
        "aizawl_id": aizawl["properties"]["district_id"],
        "duplicate_state_ids": 0,
        "duplicate_district_ids": 0,
        "null_empty_invalid_geometries": 0,
        "missing_state_relations": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
