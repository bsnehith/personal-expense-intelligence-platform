"""GenAI coach service."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from coach import monthly_json, stream_chat, stream_monthly_summary, stream_statement_summary
from metrics import metrics_response

ML_SERVICE_URL = os.environ.get("ML_SERVICE_URL", "http://ml-service:8001").rstrip("/")
MONTHLY_AUTO_ENABLED = os.environ.get("MONTHLY_AUTO_REVIEW_ENABLED", "1") == "1"
MONTHLY_AUTO_USER_ID = os.environ.get("MONTHLY_AUTO_REVIEW_USER_ID", "default")
MONTHLY_AUTO_POLL_SEC = max(300, int(os.environ.get("MONTHLY_AUTO_REVIEW_POLL_SEC", "3600")))
MONTHLY_AUTO_TXN_LIMIT = max(10, int(os.environ.get("MONTHLY_AUTO_REVIEW_TXN_LIMIT", "1500")))

_auto_task: asyncio.Task | None = None
_latest_monthly: dict[str, dict[str, Any]] = {}


def _current_period() -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


async def _generate_monthly_for_user(user_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(
            f"{ML_SERVICE_URL}/transactions/recent",
            params={"user_id": user_id, "limit": MONTHLY_AUTO_TXN_LIMIT},
        )
        r.raise_for_status()
        tx = (r.json() or {}).get("transactions") or []
    data = await monthly_json(tx)
    payload = {
        "period": _current_period(),
        "user_id": user_id,
        "generated_by": "backend_scheduler",
        "transactions_used": len(tx),
        "result": data,
    }
    _latest_monthly[user_id] = payload
    return payload


async def _monthly_scheduler_loop() -> None:
    if not MONTHLY_AUTO_ENABLED:
        return
    last_period = ""
    while True:
        try:
            period = _current_period()
            if period != last_period:
                await _generate_monthly_for_user(MONTHLY_AUTO_USER_ID)
                last_period = period
        except Exception:
            pass
        await asyncio.sleep(MONTHLY_AUTO_POLL_SEC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _auto_task
    _auto_task = asyncio.create_task(_monthly_scheduler_loop())
    yield
    if _auto_task:
        _auto_task.cancel()
        try:
            await _auto_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="GenAI Service", lifespan=lifespan)


@app.get("/metrics")
def prometheus_metrics():
    return metrics_response()


class CoachBody(BaseModel):
    question: str = ""
    transactions: list[Any] = []


class MonthlyBody(BaseModel):
    transactions: list[Any] = []


class StatementBody(BaseModel):
    transactions: list[Any] = []
    source_file: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/coach/stream")
async def coach_stream(body: CoachBody):
    async def gen():
        async for token in stream_chat(body.question, body.transactions):
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n".encode("utf-8")
        yield f"data: {json.dumps({'done': True})}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/coach/monthly")
async def coach_monthly(body: MonthlyBody):
    data = await monthly_json(body.transactions)
    return data


@app.get("/coach/monthly/latest")
async def coach_monthly_latest(user_id: str = "default"):
    cached = _latest_monthly.get(user_id)
    if cached:
        return cached
    try:
        return await _generate_monthly_for_user(user_id)
    except Exception:
        return {
            "period": _current_period(),
            "user_id": user_id,
            "generated_by": "backend_scheduler",
            "transactions_used": 0,
            "result": {"text": "", "error": "No cached monthly review available yet"},
        }


@app.post("/coach/monthly/stream")
async def coach_monthly_stream(body: MonthlyBody):
    """SSE: monthly review streamed token-by-token."""

    async def gen():
        async for token in stream_monthly_summary(body.transactions):
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n".encode("utf-8")
        yield f"data: {json.dumps({'done': True})}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/coach/statement")
async def coach_statement(body: StatementBody):
    """SSE: statement upload summary (spec §3.2.5 trigger 1)."""

    async def gen():
        async for token in stream_statement_summary(body.transactions, body.source_file):
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n".encode("utf-8")
        yield f"data: {json.dumps({'done': True})}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")
