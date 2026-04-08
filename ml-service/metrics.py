"""Prometheus metrics (spec §7.1)."""
from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# Histograms
categorisation_latency_ms = Histogram(
    "categorisation_latency_ms",
    "Time from raw txn to category assigned",
    buckets=(5, 10, 25, 50, 100, 200, 350, 500, 1000, 2000),
)
categorisation_confidence = Histogram(
    "categorisation_confidence",
    "Model confidence distribution",
    buckets=(0.1, 0.2, 0.35, 0.5, 0.65, 0.75, 0.85, 0.95, 1.0),
)

# Gauges
low_confidence_rate = Gauge(
    "low_confidence_rate",
    "Fraction of last window with conf < 0.65 (approx)",
)
model_accuracy_current = Gauge(
    "model_accuracy_current",
    "Eval accuracy from latest metadata",
)

# Counters
user_corrections_total = Counter(
    "user_corrections_total",
    "User corrections",
    ["category"],
)
anomalies_detected_total = Counter(
    "anomalies_detected_total",
    "Anomalies",
    ["type"],
)
kafka_consumer_lag_ms = Gauge(
    "kafka_consumer_lag_ms",
    "Approx consumer processing lag in milliseconds (best-effort)",
)
kafka_consumer_lag = Gauge(
    "kafka_consumer_lag",
    "Approx consumer processing lag in milliseconds (spec alias)",
)

_lf_window: list[bool] = []
_LF_WIN = 200


def observe_low_confidence(review_required: bool) -> None:
    _lf_window.append(review_required)
    if len(_lf_window) > _LF_WIN:
        _lf_window.pop(0)
    if _lf_window:
        low_confidence_rate.set(sum(_lf_window) / len(_lf_window))


def metrics_response():
    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
