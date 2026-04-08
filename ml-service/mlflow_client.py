"""Low-overhead MLflow runtime metrics logger (safe no-op when unconfigured)."""
from __future__ import annotations

import os
import threading
import time

try:
    import mlflow
except Exception:  # pragma: no cover
    mlflow = None

_LOCK = threading.Lock()
_BUFFER_COUNT = 0
_BUFFER_CONFIDENCE_SUM = 0.0
_LAST_FLUSH_TS = 0.0

_FLUSH_EVERY_SEC = float(os.environ.get("MLFLOW_RUNTIME_FLUSH_SEC", "30"))
_MIN_BATCH = int(os.environ.get("MLFLOW_RUNTIME_MIN_BATCH", "25"))
_EXPERIMENT = os.environ.get("MLFLOW_RUNTIME_EXPERIMENT", "expense-runtime")


def _enabled() -> bool:
    return bool(mlflow is not None and os.environ.get("MLFLOW_TRACKING_URI"))


def _flush(now: float) -> None:
    global _BUFFER_COUNT, _BUFFER_CONFIDENCE_SUM, _LAST_FLUSH_TS
    if _BUFFER_COUNT <= 0:
        return
    avg_conf = _BUFFER_CONFIDENCE_SUM / float(_BUFFER_COUNT)
    count = int(_BUFFER_COUNT)
    _BUFFER_COUNT = 0
    _BUFFER_CONFIDENCE_SUM = 0.0
    _LAST_FLUSH_TS = now

    try:
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment(_EXPERIMENT)
        with mlflow.start_run(run_name="runtime-metrics", nested=True):
            mlflow.log_metrics(
                {
                    "runtime_batch_count": count,
                    "runtime_avg_confidence": float(avg_conf),
                }
            )
    except Exception:
        # Never fail inference path because of telemetry.
        return


def log_metrics(**kwargs) -> None:
    """Called from inference path; aggregates and periodically flushes to MLflow."""
    if not _enabled():
        return
    conf = kwargs.get("confidence")
    if conf is None:
        return
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        return

    now = time.time()
    with _LOCK:
        global _BUFFER_COUNT, _BUFFER_CONFIDENCE_SUM
        _BUFFER_COUNT += 1
        _BUFFER_CONFIDENCE_SUM += conf
        if _BUFFER_COUNT >= _MIN_BATCH or (now - _LAST_FLUSH_TS) >= _FLUSH_EVERY_SEC:
            _flush(now)
