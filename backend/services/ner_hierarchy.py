"""Read-only loader for the validated Northeast administrative hierarchy."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_NER_DIR = _DATA_DIR / "geodata" / "ner"


def _load_feature_collection(filename: str) -> dict[str, Any]:
    path = _NER_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"NER hierarchy file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if document.get("type") != "FeatureCollection":
        raise ValueError(f"NER hierarchy file is not a FeatureCollection: {path}")
    return document


@lru_cache(maxsize=1)
def load_states() -> dict[str, Any]:
    return _load_feature_collection("states.geojson")


@lru_cache(maxsize=1)
def load_districts() -> dict[str, Any]:
    return _load_feature_collection("districts.geojson")


@lru_cache(maxsize=1)
def load_region() -> dict[str, Any]:
    return _load_feature_collection("ner_boundary.geojson")


def _properties(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("NER hierarchy feature has no properties object")
    return properties


def get_state(state_id: str) -> dict[str, Any] | None:
    normalized = state_id.upper()
    return next(
        (
            feature
            for feature in load_states()["features"]
            if _properties(feature).get("state_id") == normalized
        ),
        None,
    )


def get_district(district_id: str) -> dict[str, Any] | None:
    normalized = district_id.upper()
    return next(
        (
            feature
            for feature in load_districts()["features"]
            if _properties(feature).get("district_id") == normalized
        ),
        None,
    )


def get_districts_for_state(state_id: str) -> list[dict[str, Any]]:
    normalized = state_id.upper()
    return [
        feature
        for feature in load_districts()["features"]
        if _properties(feature).get("state_id") == normalized
    ]

