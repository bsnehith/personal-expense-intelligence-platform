"""GenAI coach service."""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from coach import monthly_json, stream_chat, stream_monthly_summary, stream_statement_summary
from metrics import metrics_response

app = FastAPI(title="GenAI Service")


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
