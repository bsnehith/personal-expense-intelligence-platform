"""Statement upload: PDF/CSV/XLSX → Kafka raw_transactions + Redis queue (or sync classify fallback)."""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from typing import Any, AsyncIterator, Callable

import httpx
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response, StreamingResponse
from kafka import KafkaProducer
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest

from normaliser import normalise_row
from parsers.csv_parser import parse_csv
from parsers.pdf_parser import parse_pdf
from parsers.xlsx_parser import parse_xlsx

ML_URL = os.environ.get("ML_SERVICE_URL", "http://localhost:8001").rstrip("/")
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
RAW_TOPIC = os.environ.get("KAFKA_RAW_TOPIC", "raw_transactions")
USE_KAFKA_PATH = os.environ.get("USE_KAFKA_UPLOAD_PATH", "1") == "1"
# Keep batch classify as fallback/override, but default architecture should use unified Kafka path.
USE_CLASSIFY_BATCH = os.environ.get("USE_CLASSIFY_BATCH", "0") == "1"
CLASSIFY_BATCH_CHUNK = max(1, int(os.environ.get("CLASSIFY_BATCH_CHUNK", "50")))
REDIS_URL = os.environ.get("REDIS_URL")
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls"}

statement_parse_latency_ms = Histogram(
    "statement_parse_latency_ms",
    "End-to-end statement parse + categorise (milliseconds)",
    buckets=(500, 1000, 2000, 5000, 10000, 20000, 30000, 60000, 120000),
)
statement_parse_success_rate = Gauge(
    "statement_parse_success_rate",
    "Ratio of successful uploads (cumulative since start)",
)
_parse_lock = threading.Lock()
_parse_ok = 0
_parse_total = 0


def _observe_parse_outcome(success: bool) -> None:
    global _parse_ok, _parse_total
    with _parse_lock:
        _parse_total += 1
        if success:
            _parse_ok += 1
        statement_parse_success_rate.set(_parse_ok / max(_parse_total, 1))


def _observe_parse_latency_ms(t0: float) -> None:
    statement_parse_latency_ms.observe((time.perf_counter() - t0) * 1000)


app = FastAPI(title="Parser Service")


def _redis():
    if not REDIS_URL:
        return None
    try:
        import redis as R

        return R.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _producer():
    try:
        return KafkaProducer(
            bootstrap_servers=BOOTSTRAP.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k if isinstance(k, bytes) else str(k).encode("utf-8"),
            linger_ms=5,
        )
    except Exception:
        return None


async def _classify(client: httpx.AsyncClient, txn: dict) -> dict:
    r = await client.post(f"{ML_URL}/classify", json=txn, timeout=120.0)
    r.raise_for_status()
    data = r.json()
    return data.get("txn") or data


async def _classify_batch(client: httpx.AsyncClient, payloads: list[dict]) -> list[dict]:
    if not payloads:
        return []
    r = await client.post(
        f"{ML_URL}/classify_batch",
        json={"transactions": payloads},
        timeout=httpx.Timeout(600.0, connect=30.0),
    )
    r.raise_for_status()
    data = r.json()
    return data.get("transactions") or []


def _detect_parser(filename: str, content: bytes) -> tuple[str, Callable[..., Any]]:
    """Pick parser by extension; PDF also detected by magic bytes (%PDF)."""
    lower = (filename or "").lower()
    if len(content) >= 4 and content[:4] == b"%PDF":
        return "pdf", parse_pdf
    if lower.endswith(".csv"):
        return "csv", parse_csv
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return "xlsx", parse_xlsx
    if lower.endswith(".pdf"):
        return "pdf", parse_pdf
    return "csv", parse_csv


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/parse")
async def parse_upload(file: UploadFile = File(...)):
    content = await file.read()
    name = file.filename or "upload"
    lower = name.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS):
        async def unsupported() -> AsyncIterator[bytes]:
            yield _sse(
                {
                    "step": "error",
                    "label": "Unsupported file type. Use only PDF, CSV, or Excel (.xlsx/.xls).",
                    "done": 0,
                    "total": 0,
                }
            )

        return StreamingResponse(unsupported(), media_type="text/event-stream")
    t0 = time.perf_counter()

    async def events() -> AsyncIterator[bytes]:
        fmt, parser_fn = _detect_parser(name, content)
        yield _sse(
            {"step": "detect", "label": f"Format: {fmt.upper()}", "done": 0, "total": 0}
        )
        pdf_note = " Scanned PDFs may take 30–120s (OCR)." if fmt == "pdf" else ""
        yield _sse(
            {
                "step": "extract",
                "label": f"Extracting transactions…{pdf_note}",
                "done": 0,
                "total": 0,
                "indeterminate": True,
            }
        )
        await asyncio.sleep(0)
        try:
            # CPU-heavy PDF parsing must not block the event loop (keeps SSE alive for clients/proxies).
            raw_rows = await asyncio.to_thread(parser_fn, content, name)
        except Exception as e:
            msg = str(e)
            if "File is not a zip file" in msg:
                msg = (
                    "Invalid Excel format: this file appears mislabeled or corrupted. "
                    "Please re-save/export as .xlsx or CSV and upload again."
                )
            yield _sse({"step": "error", "label": msg, "done": 0, "total": 0})
            _observe_parse_latency_ms(t0)
            _observe_parse_outcome(False)
            return

        if not raw_rows:
            yield _sse(
                {
                    "step": "error",
                    "label": "No transaction rows extracted",
                    "done": 0,
                    "total": 0,
                }
            )
            _observe_parse_latency_ms(t0)
            _observe_parse_outcome(False)
            return

        total = len(raw_rows)
        yield _sse(
            {
                "step": "extract",
                "label": f"Found {total} rows — starting categorisation",
                "done": 0,
                "total": total,
                "indeterminate": False,
            }
        )

        payloads: list[dict] = []
        for row in raw_rows:
            canon = normalise_row(row, name)
            payloads.append(
                {
                    "txn_id": canon["txn_id"],
                    "merchant_raw": canon["merchant_raw"],
                    "description": canon.get("description", ""),
                    "amount": canon["amount"],
                    "debit_credit": canon["debit_credit"],
                    "currency": canon.get("currency", "INR"),
                    "date": canon.get("date"),
                    "timestamp": None,
                    "source": "statement_upload",
                    "source_file": name,
                }
            )

        producer = _producer()
        rds = _redis()
        use_kafka = USE_KAFKA_PATH and producer is not None and rds is not None

        if use_kafka:
            sid = str(uuid.uuid4())
            for p in payloads:
                p["upload_session_id"] = sid
                producer.send(RAW_TOPIC, key=sid.encode(), value=p)
            await asyncio.to_thread(producer.flush)

            for i in range(total):
                item = await asyncio.to_thread(
                    lambda: rds.blpop([f"upload:queue:{sid}"], timeout=180),
                )
                if not item:
                    yield _sse(
                        {
                            "step": "error",
                            "label": "Timed out waiting for categorisation",
                            "done": i,
                            "total": total,
                        }
                    )
                    _observe_parse_latency_ms(t0)
                    _observe_parse_outcome(False)
                    return
                _, raw = item
                enriched = json.loads(raw)
                yield _sse(
                    {
                        "step": "progress",
                        "label": "Categorising…",
                        "done": i + 1,
                        "total": total,
                        "txn": enriched,
                    }
                )
        elif USE_CLASSIFY_BATCH:
            enriched_list: list[dict] = []
            try:
                async with httpx.AsyncClient() as client:
                    for start in range(0, len(payloads), CLASSIFY_BATCH_CHUNK):
                        chunk = payloads[start : start + CLASSIFY_BATCH_CHUNK]
                        end = start + len(chunk)
                        yield _sse(
                            {
                                "step": "categorise",
                                "label": f"ML categorisation: batch {start + 1}-{end} of {total} rows…",
                                "done": start,
                                "total": total,
                            }
                        )
                        await asyncio.sleep(0)
                        part = await _classify_batch(client, chunk)
                        if len(part) != len(chunk):
                            yield _sse(
                                {
                                    "step": "error",
                                    "label": (
                                        f"Batch chunk mismatch: expected {len(chunk)} "
                                        f"responses, got {len(part)}"
                                    ),
                                    "done": start,
                                    "total": total,
                                }
                            )
                            _observe_parse_latency_ms(t0)
                            _observe_parse_outcome(False)
                            return
                        enriched_list.extend(part)
                        for i, enriched in enumerate(part):
                            yield _sse(
                                {
                                    "step": "progress",
                                    "label": "Categorising…",
                                    "done": start + i + 1,
                                    "total": total,
                                    "txn": enriched,
                                }
                            )
            except Exception as e:
                yield _sse(
                    {
                        "step": "error",
                        "label": f"Categorisation failed: {e}",
                        "done": 0,
                        "total": total,
                    }
                )
                _observe_parse_latency_ms(t0)
                _observe_parse_outcome(False)
                return
            if len(enriched_list) != total:
                yield _sse(
                    {
                        "step": "error",
                        "label": f"Batch size mismatch: expected {total}, got {len(enriched_list)}",
                        "done": 0,
                        "total": total,
                    }
                )
                _observe_parse_latency_ms(t0)
                _observe_parse_outcome(False)
                return
        else:
            async with httpx.AsyncClient() as client:
                for i, payload in enumerate(payloads, start=1):
                    try:
                        enriched = await _classify(client, payload)
                    except Exception as e:
                        yield _sse(
                            {
                                "step": "error",
                                "label": f"Categorisation failed: {e}",
                                "done": i,
                                "total": total,
                            }
                        )
                        _observe_parse_latency_ms(t0)
                        _observe_parse_outcome(False)
                        return
                    yield _sse(
                        {
                            "step": "progress",
                            "label": "Categorising…",
                            "done": i,
                            "total": total,
                            "txn": enriched,
                        }
                    )

        yield _sse({"step": "done", "label": "Done", "done": total, "total": total})
        _observe_parse_latency_ms(t0)
        _observe_parse_outcome(True)

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse(obj: dict) -> bytes:
    return f"data: {json.dumps(obj, default=str)}\n\n".encode("utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}
