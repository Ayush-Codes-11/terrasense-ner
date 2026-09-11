# Phases 7–10 offline readiness

This slice makes the operational boundary explicit without pretending that
production infrastructure is already connected.

## Phase 7 — connectivity and ingestion readiness

`GET /operations/status` reports backend connectivity, Kafka, IoT gateway,
live remote-sensing feeds, and offline field-report availability separately.
Kafka and the sensor gateway currently return `NOT_CONFIGURED`; this is
intentional. The field-report queue is available in IndexedDB and retries when
the browser is online.

## Phase 8 — responder priority

The existing `/priority/{zone_id}` endpoint remains a transparent,
non-official decision-support priority calculation using mapped exposure and
the prototype risk outlook. It must not be described as an official emergency
standard or calibrated probability.

## Phase 9 — offline field PWA

The existing field-report page stores GPS reports in IndexedDB before trying
the API. Reports carry `LOCAL_ONLY`, `SYNC_PENDING`, `SYNCING`, `SYNCED`, or
`SYNC_FAILED` states. A browser `online` event retries pending reports.
Photo validation is not configured yet, so the UI does not claim that an
uploaded image has been verified by OpenCV or a vision model.

## Phase 10 — verification loop

The dashboard's Data Status panel displays the operation status and
deployment-parity result. `PASS` means the checked canonical/mirror files are
identical; `UNAVAILABLE` means those files are absent in the current checkout,
and is not represented as a pass.

## Offline preview

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` (or the port printed by Vite). With the backend
stopped, the map deliberately shows `Sample fallback · backend offline` while
the field-report form and local queue remain usable. This is the safe demo
mode; it does not claim live weather, IoT, Kafka, or remote-sensing feeds.
