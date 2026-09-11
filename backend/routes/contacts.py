"""Official emergency-contact references for demo display only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/contacts", tags=["contacts"])
_CONTACTS = Path(__file__).resolve().parent.parent / "data" / "reference" / "emergency_contacts.json"


@router.get("/official", response_model=dict[str, Any])
def official_contacts() -> dict[str, Any]:
    with _CONTACTS.open(encoding="utf-8") as handle:
        return json.load(handle)
