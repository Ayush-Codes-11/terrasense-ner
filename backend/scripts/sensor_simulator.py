"""Publish clearly labelled demo telemetry to the local Kafka-compatible broker."""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone


def build_event(device_id: str, lat: float, lon: float, sequence: int) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "sensor.telemetry",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "device_id": device_id,
        "latitude": lat,
        "longitude": lon,
        "measurements": {
            "soil_moisture": round(0.45 + (sequence % 10) * 0.01, 3),
            "pore_pressure_kpa": round(18.0 + (sequence % 5) * 0.4, 2),
            "inclinometer_mm": round((sequence % 8) * 0.2, 2),
        },
        "provenance": {
            "status": "SIMULATED",
            "source": "TerraSense local sensor simulator",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=0, help="0 means run until stopped")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--device-id", default="SIM-AIZAWL-001")
    parser.add_argument("--lat", type=float, default=23.7271)
    parser.add_argument("--lon", type=float, default=92.7176)
    args = parser.parse_args()

    try:
        from confluent_kafka import Producer
    except ImportError as exc:
        raise SystemExit(
            "Install backend/requirements-local.txt before running the simulator."
        ) from exc

    producer = Producer(
        {"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")}
    )
    topic = os.getenv("KAFKA_SENSOR_TOPIC", "terrasense.sensor.telemetry")
    sequence = 0
    while args.count == 0 or sequence < args.count:
        event = build_event(args.device_id, args.lat, args.lon, sequence)
        producer.produce(topic, json.dumps(event).encode("utf-8"))
        producer.flush(5)
        print(json.dumps(event), flush=True)
        sequence += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
