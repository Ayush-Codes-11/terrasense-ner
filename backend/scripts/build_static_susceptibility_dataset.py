"""Build a reproducible static-susceptibility table from real pilot data.

This is a feature-table preparation step, not model training. The GSI public
inventory has no event dates, so this output must not be used for temporal
rainfall-trigger validation or presented as calibrated probability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape

from services.gsi_inventory import get_all_mizoram_records
from services.terrain_loader import get_zone_terrain


ROOT = Path(__file__).resolve().parents[2]
GRID_PATH = ROOT / "data" / "sample" / "grid-risk.geojson"
DEFAULT_OUTPUT = ROOT / "data" / "real" / "landslides" / "static_susceptibility_dataset.json"


def _point(record: dict[str, Any]) -> Point | None:
    attrs = record.get("attributes", {})
    geom = record.get("geometry", {})
    lat = attrs.get("latitude") or attrs.get("u_lat") or geom.get("y")
    lon = attrs.get("longitude") or attrs.get("u_long") or geom.get("x")
    try:
        return Point(float(lon), float(lat))
    except (TypeError, ValueError):
        return None


def build_dataset() -> dict[str, Any]:
    with GRID_PATH.open(encoding="utf-8") as handle:
        features = json.load(handle)["features"]
    records = get_all_mizoram_records()
    rows = []
    for feature in features:
        props = feature["properties"]
        zone_id = str(props["zone_id"]).upper()
        polygon = shape(feature["geometry"])
        inventory_count = sum(
            1
            for record in records
            if (point := _point(record)) is not None and polygon.covers(point)
        )
        terrain = get_zone_terrain(zone_id) or {}
        rows.append(
            {
                "zone_id": zone_id,
                "state_id": "IN-MZ",
                "district_id": "IND-ADM2-76128533B34203923268864",
                "mean_slope_deg": terrain.get("mean_slope_deg"),
                "p90_slope_deg": terrain.get("p90_slope_deg"),
                "mean_elevation_m": terrain.get("mean_elevation_m"),
                "elevation_range_m": terrain.get("elevation_range_m"),
                "gsi_inventory_count": inventory_count,
                "inventory_presence_label": int(inventory_count > 0),
            }
        )
    return {
        "dataset_type": "STATIC_SUSCEPTIBILITY_FEATURE_TABLE",
        "label_semantics": "spatial_inventory_presence_only",
        "model_status": "NOT_TRAINED",
        "is_probability": False,
        "sources": {
            "grid": "TerraSense Aizawl pilot analysis grid (existing A01-E05)",
            "terrain": "Copernicus DEM GLO-30 derived zonal statistics",
            "inventory": "GSI BhooSanket Landslide_Public",
        },
        "limitations": [
            "GSI public records contain no usable event dates.",
            "Inventory presence is not a temporal event label.",
            "Rows are pilot-grid cells and are not a national training sample.",
            "A future model requires spatial holdout validation and additional static covariates.",
        ],
        "row_count": len(rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    dataset = build_dataset()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {dataset['row_count']} rows to {args.output}")


if __name__ == "__main__":
    main()
