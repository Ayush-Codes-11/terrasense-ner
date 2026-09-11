# Local integration setup

This is a development/demo stack, not a production deployment.

## Install

Requirements:

- Docker Desktop with Compose
- Python 3.12+
- Node.js/npm for the existing frontend
- Optional NASA Earthdata account/token for refresh scripts

```powershell
cd backend
py -m pip install -r requirements.txt
py -m pip install -r requirements-local.txt
cd ..\frontend
npm install
```

## Start PostGIS and Kafka-compatible Redpanda

From the repository root:

```powershell
docker compose up -d
```

Redpanda listens on `localhost:19092`; PostGIS listens on `localhost:5432`.
The credentials are intentionally local-only demo credentials. Change them
before sharing a deployment.

Copy `backend/.env.local.example` to `backend/.env.local` and load it in the
shell or your IDE. The sensor simulator is intentionally marked
`SIMULATED`:

```powershell
$env:PYTHONPATH="backend"
py backend\scripts\sensor_simulator.py --count 3 --interval 2
```

The simulator demonstrates the telemetry contract but is not a substitute for
inclinometers, pore-pressure sensors, or soil-moisture hardware.

## OpenCV screening

`backend/services/photo_screening.py` provides a conservative image-quality
and line-candidate screen. It reports `OPENCV_SCREENING_ONLY` and always
requires human verification. It does not claim a trained landslide classifier.

## What still needs external access

- NASA Earthdata credentials and network access for fresh GPM/SMAP downloads.
- Approved IMD, ISRO, Sentinel, or other provider credentials/API access.
- Real sensor hardware, gateway protocol, calibration, and deployment network.
- Production Kafka/PostgreSQL secrets, backups, monitoring, and alert provider.

Never commit `.env.local`, tokens, passwords, or production credentials.
