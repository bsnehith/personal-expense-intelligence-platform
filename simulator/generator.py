"""Kafka producer: publishes synthetic transactions to raw_transactions."""
import json
import os
import sys
import time

from kafka import KafkaProducer
from kafka.errors import KafkaError

from templates import build_transaction

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
TOPIC = os.environ.get("KAFKA_RAW_TOPIC", "raw_transactions")
# Spec: up to ~10 tx/sec load testing — use e.g. TX_INTERVAL_SEC=0.1
INTERVAL = max(0.001, float(os.environ.get("TX_INTERVAL_SEC", "5")))
# Wait for Docker Kafka to become ready (seconds); set 0 to fail fast
_KAFKA_WAIT_SEC = float(os.environ.get("SIMULATOR_KAFKA_WAIT_SEC", "120"))
_KAFKA_RETRY_SEC = float(os.environ.get("SIMULATOR_KAFKA_RETRY_SEC", "2"))


def _create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=5,
    )


def _wait_for_kafka() -> KafkaProducer:
    if _KAFKA_WAIT_SEC <= 0:
        return _create_producer()
    deadline = time.monotonic() + _KAFKA_WAIT_SEC
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return _create_producer()
        except KafkaError as exc:
            last_err = exc
            remaining = max(0.0, deadline - time.monotonic())
            print(
                f"[simulator] Kafka not ready at {BOOTSTRAP!r} ({exc!s}); "
                f"retry in {_KAFKA_RETRY_SEC:.0f}s ({remaining:.0f}s left)...",
                flush=True,
            )
            time.sleep(_KAFKA_RETRY_SEC)
    print(
        "[simulator] No Kafka broker at "
        f"{BOOTSTRAP!r} after {_KAFKA_WAIT_SEC:.0f}s.\n"
        "  Start brokers from the repo root, e.g.:\n"
        "    docker compose up -d zookeeper kafka\n"
        "  Host apps use PLAINTEXT_HOST on port 29092 (see docker-compose.yml).\n"
        "  Override: cmd: set KAFKA_BOOTSTRAP_SERVERS=host:port\n"
        "           PowerShell: $env:KAFKA_BOOTSTRAP_SERVERS='host:port'",
        file=sys.stderr,
        flush=True,
    )
    raise SystemExit(1) from last_err


def main() -> None:
    producer = _wait_for_kafka()
    print(f"[simulator] Kafka={BOOTSTRAP} topic={TOPIC} interval={INTERVAL}s", flush=True)
    while True:
        payload = build_transaction()
        producer.send(TOPIC, value=payload)
        producer.flush()
        print(f"[simulator] sent {payload['txn_id']} {payload['merchant_raw'][:48]}...", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
