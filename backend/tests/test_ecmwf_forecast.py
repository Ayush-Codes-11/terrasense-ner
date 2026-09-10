import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.scripts.fetch_ecmwf_forecast import process_ecmwf_response

def test_process_ecmwf_response_valid():
    f1_date = datetime(2026, 9, 9, tzinfo=timezone.utc)
    run_str = "2026-09-09T00:00"

    # Generate 168 hours of dummy data starting from 00:00
    hourly_time = [(f1_date + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(168)]
    # Set precipitaiton values where hours 1-24 are 1.0, 25-48 are 2.0, 49-72 are 3.0
    hourly_precip = [0.0] * 168
    for i in range(1, 73):
        if i <= 24:
            hourly_precip[i] = 1.0
        elif i <= 48:
            hourly_precip[i] = 2.0
        else:
            hourly_precip[i] = 3.0

    centroids = {f"Z{i:02d}": (23.72, 92.71) for i in range(25)}
    sorted_zids = sorted(centroids.keys())

    res = [{
        "latitude": 23.75,
        "longitude": 92.75,
        "hourly_units": {"precipitation": "mm"},
        "hourly": {
            "time": hourly_time,
            "precipitation": hourly_precip.copy()
        }
    } for _ in range(25)]

    out, uniq_count = process_ecmwf_response(res, sorted_zids, centroids, f1_date, run_str)

    assert uniq_count == 1
    assert out["metadata"]["data_type"] == "REAL_FORECAST"
    assert out["metadata"]["model"] == "IFS_HRES"

    zone_data = out["zones"]["Z00"]
    assert zone_data["grid_cell_id"] == "ECMWF_23.75000_92.75000"
    assert zone_data["forecast_interval_mm"]["0_24h"] == 24.0
    assert zone_data["forecast_interval_mm"]["24_48h"] == 48.0
    assert zone_data["forecast_interval_mm"]["48_72h"] == 72.0


def test_process_ecmwf_negative_value_rejected():
    f1_date = datetime(2026, 9, 9, tzinfo=timezone.utc)
    run_str = "2026-09-09T00:00"
    hourly_time = [(f1_date + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(168)]
    hourly_precip = [1.0] * 168

    centroids = {f"Z{i:02d}": (23.72, 92.71) for i in range(25)}
    sorted_zids = sorted(centroids.keys())

    res = [{
        "latitude": 23.75,
        "longitude": 92.75,
        "hourly_units": {"precipitation": "mm"},
        "hourly": {"time": hourly_time.copy(), "precipitation": hourly_precip.copy()}
    } for _ in range(25)]

    res[0]["hourly"]["precipitation"][10] = -1.0

    with pytest.raises(ValueError, match="Invalid precipitation value -1.0"):
        process_ecmwf_response(res, sorted_zids, centroids, f1_date, run_str)


def test_process_ecmwf_null_value_rejected():
    f1_date = datetime(2026, 9, 9, tzinfo=timezone.utc)
    run_str = "2026-09-09T00:00"
    hourly_time = [(f1_date + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(168)]
    hourly_precip = [1.0] * 168

    centroids = {f"Z{i:02d}": (23.72, 92.71) for i in range(25)}
    sorted_zids = sorted(centroids.keys())

    res = [{
        "latitude": 23.75,
        "longitude": 92.75,
        "hourly_units": {"precipitation": "mm"},
        "hourly": {"time": hourly_time.copy(), "precipitation": hourly_precip.copy()}
    } for _ in range(25)]

    res[0]["hourly"]["precipitation"][5] = None

    with pytest.raises(ValueError, match="Invalid precipitation value None"):
        process_ecmwf_response(res, sorted_zids, centroids, f1_date, run_str)


def test_process_ecmwf_incorrect_unit_rejected():
    f1_date = datetime(2026, 9, 9, tzinfo=timezone.utc)
    run_str = "2026-09-09T00:00"
    hourly_time = [(f1_date + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(168)]
    hourly_precip = [1.0] * 168

    centroids = {f"Z{i:02d}": (23.72, 92.71) for i in range(25)}
    sorted_zids = sorted(centroids.keys())

    res = [{
        "latitude": 23.75,
        "longitude": 92.75,
        "hourly_units": {"precipitation": "mm"},
        "hourly": {"time": hourly_time.copy(), "precipitation": hourly_precip.copy()}
    } for _ in range(25)]

    res[0]["hourly_units"]["precipitation"] = "cm"

    with pytest.raises(ValueError, match="Unexpected precipitation unit"):
        process_ecmwf_response(res, sorted_zids, centroids, f1_date, run_str)


def test_process_ecmwf_timestamp_mismatch_rejected():
    f1_date = datetime(2026, 9, 9, tzinfo=timezone.utc)
    run_str = "2026-09-09T00:00"
    hourly_time = [(f1_date + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(168)]
    hourly_precip = [1.0] * 168

    centroids = {f"Z{i:02d}": (23.72, 92.71) for i in range(25)}
    sorted_zids = sorted(centroids.keys())

    res = [{
        "latitude": 23.75,
        "longitude": 92.75,
        "hourly_units": {"precipitation": "mm"},
        "hourly": {"time": hourly_time.copy(), "precipitation": hourly_precip.copy()}
    } for _ in range(25)]

    res[0]["hourly"]["time"][10] = "2026-09-09T11:00"

    with pytest.raises(ValueError, match="Timestamp mismatch"):
        process_ecmwf_response(res, sorted_zids, centroids, f1_date, run_str)


from unittest.mock import patch
from backend.services.forecast_loader import get_forecast_provenance_status

@patch("backend.services.forecast_loader._load_ecmwf_forecast_file")
@patch("backend.services.forecast_loader.load_gpm_observed_dataset")
def test_freshness_current_date_equals_f1(mock_gpm, mock_load):
    mock_gpm.return_value = {"metadata": {"days": {"d0": "2026-09-08"}}}
    mock_load.return_value = {
        "metadata": {
            "data_type": "REAL_FORECAST",
            "source_data_origin": "ECMWF_OPEN_METEO",
            "days": {"f1": "2026-09-09"}
        }
    }
    # Current UTC is exactly f1
    current_utc = datetime(2026, 9, 9, tzinfo=timezone.utc)
    res = get_forecast_provenance_status(current_utc=current_utc)

    assert res["status"] == "REAL_FORECAST"
    assert res["freshness_status"] == "CURRENT"
    assert res["is_real"] is True
    assert res["is_live"] is False


@patch("backend.services.forecast_loader._load_ecmwf_forecast_file")
@patch("backend.services.forecast_loader.load_gpm_observed_dataset")
def test_freshness_current_date_greater_than_f1(mock_gpm, mock_load):
    mock_gpm.return_value = {"metadata": {"days": {"d0": "2026-09-08"}}}
    mock_load.return_value = {
        "metadata": {
            "data_type": "REAL_FORECAST",
            "source_data_origin": "ECMWF_OPEN_METEO",
            "days": {"f1": "2026-09-09"}
        }
    }
    # Current UTC is strictly greater than f1
    current_utc = datetime(2026, 9, 10, tzinfo=timezone.utc)
    res = get_forecast_provenance_status(current_utc=current_utc)

    assert res["status"] == "REAL_FORECAST"
    assert res["freshness_status"] == "STALE"
    assert res["is_real"] is True
    assert res["is_live"] is False


@patch("backend.services.forecast_loader._load_ecmwf_forecast_file")
@patch("backend.services.forecast_loader.load_gpm_observed_dataset")
def test_freshness_gpm_advanced_but_ecmwf_did_not(mock_gpm, mock_load):
    # GPM advanced to Sep 9, so F1 *should* be Sep 10
    mock_gpm.return_value = {"metadata": {"days": {"d0": "2026-09-09"}}}
    # But ECMWF file still has F1 = Sep 9
    mock_load.return_value = {
        "metadata": {
            "data_type": "REAL_FORECAST",
            "source_data_origin": "ECMWF_OPEN_METEO",
            "days": {"f1": "2026-09-09"}
        }
    }
    # Current UTC is Sep 9
    current_utc = datetime(2026, 9, 9, tzinfo=timezone.utc)
    res = get_forecast_provenance_status(current_utc=current_utc)

    assert res["status"] == "REAL_FORECAST"
    assert res["freshness_status"] == "STALE"
    assert res["is_real"] is True
    assert res["is_live"] is False
