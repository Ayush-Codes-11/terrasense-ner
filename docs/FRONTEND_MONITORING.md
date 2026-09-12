# Frontend monitoring and weather overlays

The dashboard polls `/operations/status` every 30 seconds while open. It
reports backend/API state and does not label offline snapshots as live.

An optional `VITE_WEATHER_TILE_URL` can enable a cloud/radar overlay in the
Leaflet layer picker. The value must be an approved provider tile template
containing `{z}`, `{x}`, and `{y}`. It is intentionally empty by default:
adding a random tile URL would create an unverified or potentially
rate-limited feed.

The dashboard exposes an install prompt when the browser supports PWA
installation. The service worker precaches the app shell, and field reports
with photos remain in IndexedDB until synchronization succeeds.

“AI monitoring” in this build means transparent risk/evidence status and
provenance. It is not a calibrated probability model or autonomous emergency
dispatcher.
