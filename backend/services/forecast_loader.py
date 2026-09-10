import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_DATA_DIR = _REPO_ROOT / "data" if (_REPO_ROOT / "data").exists() else _BACKEND_DIR / "data"
_ECMWF_FORECAST_FILE = _DATA_DIR / "real" / "weather" / "ecmwf_forecast.json"
try:
    from services.gpm_loader import load_gpm_observed_dataset
except ImportError:
    try:
        from backend.services.gpm_loader import load_gpm_observed_dataset
    except ImportError:
        def load_gpm_observed_dataset(): return None


@lru_cache(maxsize=1)
def _load_ecmwf_forecast_file() -> Optional[Dict[str, Any]]:
    if not _ECMWF_FORECAST_FILE.exists():
        return None
    try:
        with open(_ECMWF_FORECAST_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_forecast_provenance_status(current_utc: Optional[datetime] = None) -> Dict[str, Any]:
    data = _load_ecmwf_forecast_file()
    if not data or "metadata" not in data:
        return {"status": "SAMPLE_MOCK", "freshness_status": "MOCK", "source": "None", "is_real": False, "is_live": False}

    meta = data["metadata"]
    status = meta.get("data_type", "REAL_FORECAST")

    if current_utc is None:
        current_utc = datetime.now(timezone.utc)

    current_utc_str = current_utc.strftime("%Y-%m-%d")
    actual_f1_str = meta.get("days", {}).get("f1")

    freshness = "CURRENT"

    if actual_f1_str and actual_f1_str < current_utc_str:
        freshness = "STALE"

    gpm_data = load_gpm_observed_dataset()
    if gpm_data:
        d0_str = gpm_data.get("metadata", {}).get("days", {}).get("d0")
        if d0_str:
            try:
                gpm_d0_dt = datetime.strptime(d0_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                expected_f1_str = (gpm_d0_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            except Exception:
                import datetime as dt
                gpm_d0_dt = dt.datetime.strptime(d0_str, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
                expected_f1_str = (gpm_d0_dt + dt.timedelta(days=1)).strftime("%Y-%m-%d")

            if actual_f1_str != expected_f1_str:
                freshness = "STALE"

    return {
        "status": status,
        "freshness_status": freshness,
        "source": meta.get("source_data_origin", "ECMWF_OPEN_METEO"),
        "is_real": True,
        "is_live": False,
        "meta": meta
    }


def get_zone_forecast(zone_id: str) -> Optional[Dict[str, Any]]:
    data = _load_ecmwf_forecast_file()
    if not data or "zones" not in data:
        return None

    zid = zone_id.upper()
    return data["zones"].get(zid)
