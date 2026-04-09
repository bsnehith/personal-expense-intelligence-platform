"""ML microservice: /classify, /correct, /retrain, /model-info, /metrics + Kafka consumer."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from anomaly import anomaly_engine
from db import (
    get_transaction_payload,
    insert_transaction,
    list_recent_transactions,
    record_anomaly_action,
)
from metrics import (
    categorisation_confidence,
    categorisation_latency_ms,
    kafka_consumer_lag_ms,
    kafka_consumer_lag,
    metrics_response,
    model_accuracy_current,
    observe_low_confidence,
    user_corrections_total,
)
from metrics import anomalies_detected_total as anomalies_counter
from model.inference import Classifier, load_classifier
from model.merchant_clean import clean_merchant
from mlflow_client import log_metrics as mlflow_log_stub
from online_learning import append_correction_training_row, correction_stats, record_correction
from redis_util import push_upload_result

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
RAW_TOPIC = os.environ.get("KAFKA_RAW_TOPIC", "raw_transactions")
CAT_TOPIC = os.environ.get("KAFKA_CAT_TOPIC", "categorised_transactions")
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "model/artifacts"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
RETRAIN_THRESHOLD = int(os.environ.get("RETRAIN_CORRECTION_THRESHOLD", "50"))
RETRAIN_MAX_AGE_HOURS = float(os.environ.get("RETRAIN_MAX_AGE_HOURS", "24"))
USER_DEFAULT = "default"
_SVC_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _SVC_ROOT.parent

clf: Classifier | None = None
_consumer_task: asyncio.Task | None = None


def _train_cmd(csv: Path | None) -> list[str]:
    cmd = [sys.executable, "-m", "model.train", "--out", str(MODEL_DIR)]
    if csv is not None and csv.is_file():
        cmd.extend(["--data", str(csv)])
    if os.environ.get("USE_ALL_MODELS") == "1":
        cmd.append("--all-models")
    elif os.environ.get("USE_ENSEMBLE") == "1":
        cmd.append("--ensemble")
    elif os.environ.get("USE_EMBEDDING_MODEL") == "1":
        cmd.append("--embedding")
    return cmd


def _transactions_train_csv() -> Path | None:
    """Prefer ml-service/data, then repo-root data/ (Docker mounts ./data → /app/data)."""
    for p in (DATA_DIR / "transactions_train.csv", _REPO_ROOT / "data" / "transactions_train.csv"):
        if p.is_file():
            return p
    return None


def _maybe_train_on_boot() -> None:
    """Match docker-entrypoint.sh: train before serving when no artifacts (local uvicorn has no entrypoint)."""
    if os.environ.get("TRAIN_ON_BOOT", "1") != "1":
        return
    if (MODEL_DIR / "metadata.json").exists():
        return
    csv = _transactions_train_csv()
    cmd = _train_cmd(csv)
    env = os.environ.copy()
    if (_REPO_ROOT / "data").is_dir():
        env.setdefault("DATA_DIR", str(_REPO_ROOT / "data"))
    print("[ml-service] Training initial model (TRAIN_ON_BOOT; no model/artifacts/metadata.json)...", flush=True)
    try:
        subprocess.run(cmd, check=True, cwd=str(_SVC_ROOT), env=env)
    except subprocess.CalledProcessError as exc:
        print(
            f"[ml-service] TRAIN_ON_BOOT failed ({exc}); Kafka consumer will not start without a model. "
            "Fix errors above or run: python -m model.train --out model/artifacts",
            file=sys.stderr,
            flush=True,
        )


def _ensure_model() -> Classifier:
    global clf
    if clf is None:
        if not (MODEL_DIR / "metadata.json").exists():
            raise HTTPException(status_code=503, detail="Model not trained yet")
        clf = load_classifier(MODEL_DIR)
        meta_path = MODEL_DIR / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            model_accuracy_current.set(float(meta.get("eval_accuracy", 0)))
    return clf


def _date_from_ts(ts: str | None) -> str:
    if not ts:
        return datetime.utcnow().strftime("%Y-%m-%d")
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d")


def enrich_payload(raw: dict, source: str, source_file: str | None) -> dict:
    src = raw.get("source") or source
    sfile = raw.get("source_file") if raw.get("source_file") is not None else source_file
    t0 = time.perf_counter()
    c = _ensure_model()
    merchant_raw = raw.get("merchant_raw") or ""
    amt = float(raw.get("amount") or 0)
    desc = raw.get("description") or ""
    pred = c.predict(merchant_raw, desc, amt)
    merchant_clean = clean_merchant(merchant_raw)
    ts = raw.get("timestamp")
    user_id = raw.get("user_id") or USER_DEFAULT

    an = anomaly_engine.evaluate(
        user_id,
        pred["category"],
        amt,
        merchant_clean,
        ts,
    )

    out = {
        "txn_id": raw.get("txn_id"),
        "merchant_raw": merchant_raw,
        "merchant_clean": merchant_clean or "Unknown",
        "description": desc or merchant_clean,
        "amount": amt,
        "date": raw.get("date") or _date_from_ts(ts),
        "debit_credit": raw.get("debit_credit") or "debit",
        "currency": raw.get("currency") or "INR",
        "category": pred["category"],
        "confidence": pred["confidence"],
        "review_required": pred["review_required"],
        "alternatives": pred["alternatives"],
        "source": src,
        "source_file": sfile,
        "user_id": user_id,
        "anomaly": an,
        "upload_session_id": raw.get("upload_session_id"),
    }

    ms = (time.perf_counter() - t0) * 1000
    categorisation_latency_ms.observe(ms)
    categorisation_confidence.observe(pred["confidence"])
    observe_low_confidence(pred["review_required"])
    if an:
        for t in an.get("types", []) or []:
            anomalies_counter.labels(type=str(t)).inc()

    mlflow_log_stub(confidence=pred["confidence"])

    try:
        insert_transaction(out)
    except Exception:
        pass

    return out


async def _kafka_loop() -> None:
    for _ in range(120):
        try:
            _ensure_model()
            break
        except HTTPException:
            await asyncio.sleep(1)
    else:
        print("[ml-service] Kafka consumer not starting — no model", file=sys.stderr)
        return

    backoff = 2.0
    max_backoff = 60.0
    while True:
        consumer: AIOKafkaConsumer | None = None
        producer: AIOKafkaProducer | None = None
        try:
            consumer = AIOKafkaConsumer(
                RAW_TOPIC,
                bootstrap_servers=BOOTSTRAP,
                group_id="ml-service-categoriser",
                value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                auto_offset_reset="latest",
            )
            producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
            await consumer.start()
            await producer.start()
            print(f"[ml-service] Kafka consumer on {BOOTSTRAP} {RAW_TOPIC} -> {CAT_TOPIC}", flush=True)
            backoff = 2.0
            async for msg in consumer:
                raw = msg.value
                t_recv = time.perf_counter()
                loop = asyncio.get_event_loop()

                def _work():
                    return enrich_payload(raw, source="stream", source_file=None)

                out = await loop.run_in_executor(None, _work)
                lag_ms = (time.perf_counter() - t_recv) * 1000
                kafka_consumer_lag_ms.set(lag_ms)
                kafka_consumer_lag.set(lag_ms)

                if out.get("upload_session_id"):
                    push_upload_result(str(out["upload_session_id"]), out)

                await producer.send_and_wait(
                    CAT_TOPIC, json.dumps(out, default=str).encode("utf-8")
                )
        except Exception as exc:
            print(
                f"[ml-service] Kafka loop error: {exc!r}; retrying in {backoff:.0f}s",
                file=sys.stderr,
                flush=True,
            )
            await asyncio.sleep(backoff)
            backoff = min(max_backoff, backoff * 1.5)
        finally:
            if consumer:
                try:
                    await consumer.stop()
                except Exception:
                    pass
            if producer:
                try:
                    await producer.stop()
                except Exception:
                    pass


def _maybe_retrain_async(total_corrections: int) -> None:
    trigger_by_count = (
        RETRAIN_THRESHOLD > 0
        and total_corrections > 0
        and total_corrections % RETRAIN_THRESHOLD == 0
    )
    trigger_by_age = False
    if RETRAIN_MAX_AGE_HOURS > 0:
        meta_path = MODEL_DIR / "metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                last = meta.get("last_trained_at")
                if last:
                    last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                    age_hours = (datetime.now(last_dt.tzinfo) - last_dt).total_seconds() / 3600
                    trigger_by_age = age_hours >= RETRAIN_MAX_AGE_HOURS
            except Exception:
                trigger_by_age = False

    if trigger_by_count or trigger_by_age:

        def _run():
            csv = DATA_DIR / "transactions_train.csv"
            cmd = _train_cmd(csv if csv.is_file() else None)
            try:
                subprocess.run(cmd, check=True, cwd=str(Path(__file__).resolve().parent))
            except subprocess.CalledProcessError:
                return
            global clf
            clf = load_classifier(MODEL_DIR)

        threading.Thread(target=_run, daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(_maybe_train_on_boot)
    global _consumer_task
    _consumer_task = asyncio.create_task(_kafka_loop())
    yield
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="ML Service", lifespan=lifespan)


class TxnIn(BaseModel):
    txn_id: str | None = None
    merchant_raw: str
    description: str = ""
    amount: float
    debit_credit: str = "debit"
    currency: str = "INR"
    timestamp: str | None = None
    date: str | None = None
    user_id: str | None = None
    source: str | None = None
    source_file: str | None = None
    upload_session_id: str | None = None


class BatchClassifyIn(BaseModel):
    """Statement upload: many rows in one request (avoids per-row Kafka/HTTP latency)."""

    transactions: list[TxnIn]


_MAX_BATCH = int(os.environ.get("CLASSIFY_BATCH_MAX", "5000"))


class CorrectIn(BaseModel):
    txn_id: str
    correct_category: str
    merchant_raw: str | None = None
    description: str | None = None
    amount: float | None = None


class AnomalyActionIn(BaseModel):
    txn_id: str
    action: str
    note: str | None = None


@app.get("/metrics")
def prometheus_metrics():
    return metrics_response()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify")
def classify(body: TxnIn):
    raw = body.model_dump()
    out = enrich_payload(raw, source="api", source_file=body.source_file)
    return {
        "category": out["category"],
        "confidence": out["confidence"],
        "alternatives": out["alternatives"],
        "review_required": out["review_required"],
        "txn": out,
    }


def _classify_batch_sync(body: BatchClassifyIn) -> dict:
    """CPU-heavy; run in thread pool from async handler so other requests stay responsive."""
    txs = body.transactions
    if not txs:
        return {"transactions": []}
    outs: list[dict] = []
    for t in txs:
        raw = t.model_dump()
        out = enrich_payload(
            raw,
            source=raw.get("source") or "statement_upload",
            source_file=raw.get("source_file"),
        )
        outs.append(out)
    return {"transactions": outs}


@app.post("/classify_batch")
async def classify_batch(body: BatchClassifyIn):
    """Process a full statement in one round-trip; sequential order preserves anomaly history."""
    if len(body.transactions) > _MAX_BATCH:
        raise HTTPException(
            status_code=413,
            detail=f"Maximum {_MAX_BATCH} transactions per batch",
        )
    return await asyncio.to_thread(_classify_batch_sync, body)


@app.post("/correct")
def correct(body: CorrectIn):
    rec = record_correction(body.txn_id, body.correct_category)
    user_corrections_total.labels(category=body.correct_category).inc()
    payload = None
    if body.merchant_raw:
        payload = {
            "merchant_raw": body.merchant_raw,
            "description": body.description or "",
            "amount": body.amount if body.amount is not None else 0,
        }
    else:
        payload = get_transaction_payload(body.txn_id)
    if payload:
        append_correction_training_row(body.correct_category, payload)
    tot = int(rec.get("total_corrections") or correction_stats().get("total", 0))
    _maybe_retrain_async(tot)
    return rec


@app.post("/retrain")
def retrain():
    csv = DATA_DIR / "transactions_train.csv"
    cmd = _train_cmd(csv if csv.is_file() else None)
    try:
        subprocess.run(cmd, check=True, cwd=str(Path(__file__).resolve().parent))
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Retrain failed: {e}") from e
    global clf
    clf = load_classifier(MODEL_DIR)
    meta_path = MODEL_DIR / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model_accuracy_current.set(float(meta.get("eval_accuracy", 0)))
    return {"ok": True, "message": "Retrained and reloaded"}


@app.post("/anomaly-action")
def anomaly_action(body: AnomalyActionIn):
    action = (body.action or "").strip().lower()
    if action not in {"expected", "review"}:
        raise HTTPException(status_code=400, detail="action must be 'expected' or 'review'")
    return record_anomaly_action(body.txn_id, action, body.note)


@app.get("/transactions/recent")
def transactions_recent(user_id: str = USER_DEFAULT, limit: int = 500):
    rows = list_recent_transactions(user_id=user_id, limit=limit)
    return {"transactions": rows}


@app.get("/model-info")
def model_info():
    meta_path = MODEL_DIR / "metadata.json"
    if not meta_path.exists():
        return {
            "version": "—",
            "training_rows": 0,
            "eval_accuracy": 0,
            "last_retrained": None,
            "confusionMatrix": [],
            "correctionCounts": {},
        }
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    stats = correction_stats()
    heat = meta.get("confusion_matrix") or []
    if not heat:
        n = len(meta.get("categories", []))
        heat = [[0] * max(n, 1) for _ in range(max(n, 1))]
    return {
        "version": meta.get("version", "1.0.0"),
        "training_rows": meta.get("training_rows", 0),
        "eval_accuracy": meta.get("eval_accuracy", 0),
        "last_retrained": meta.get("last_trained_at") or meta.get("last_retrained"),
        "confusionMatrix": heat,
        "correctionCounts": stats.get("by_category", {}),
    }
