"""API gateway: CORS, SSE /feed/stream, proxies to parser / ml / genai."""
from __future__ import annotations

import asyncio
import json
import os
import uuid

import httpx
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from metrics import active_sse_feeds, metrics_response, upload_bytes_total

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
CAT_TOPIC = os.environ.get("KAFKA_CAT_TOPIC", "categorised_transactions")
# /feed/stream: wait for Kafka when running gateway on host (Docker may still be starting)
_FEED_KAFKA_WAIT_SEC = float(os.environ.get("GATEWAY_KAFKA_WAIT_SEC", "120"))
_FEED_KAFKA_RETRY_SEC = float(os.environ.get("GATEWAY_KAFKA_RETRY_SEC", "2"))
# latest = only events after this connection (default). earliest = replay topic from start (dev only; can flood UI).
_FEED_AUTO_OFFSET = os.environ.get("GATEWAY_KAFKA_AUTO_OFFSET_RESET", "latest")
ML_URL = os.environ.get("ML_SERVICE_URL", "http://localhost:8001").rstrip("/")
PARSER_URL = os.environ.get("PARSER_SERVICE_URL", "http://localhost:8002").rstrip("/")
GENAI_URL = os.environ.get("GENAI_SERVICE_URL", "http://localhost:8003").rstrip("/")

app = FastAPI(title="API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Must be False with wildcard origin; True + * is invalid CORS and breaks
    # cross-origin dev (Vite :5173 → gateway :8000) for fetch/SSE in some browsers.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def prometheus_metrics():
    return metrics_response()


@app.get("/feed/stream")
async def feed_stream():
    async def gen():
        active_sse_feeds.inc()
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + _FEED_KAFKA_WAIT_SEC
            consumer: AIOKafkaConsumer | None = None
            last_status_at = 0.0
            group_id = f"gateway-feed-{uuid.uuid4()}"

            while consumer is None and loop.time() < deadline:
                c = AIOKafkaConsumer(
                    CAT_TOPIC,
                    bootstrap_servers=BOOTSTRAP,
                    group_id=group_id,
                    value_deserializer=lambda b: json.loads(b.decode("utf-8")),
                    auto_offset_reset=_FEED_AUTO_OFFSET,
                )
                try:
                    await c.start()
                    consumer = c
                except KafkaConnectionError as exc:
                    try:
                        await c.stop()
                    except Exception:
                        pass
                    now = loop.time()
                    if now - last_status_at >= 10.0 or last_status_at == 0.0:
                        # Same SSE event name as txns so EventSource.onmessage receives it; client skips via feed_event
                        yield {
                            "event": "message",
                            "data": json.dumps(
                                {
                                    "feed_event": "waiting",
                                    "bootstrap": BOOTSTRAP,
                                    "error": str(exc),
                                }
                            ),
                        }
                        last_status_at = now
                    sleep_for = min(_FEED_KAFKA_RETRY_SEC, max(0.0, deadline - now))
                    await asyncio.sleep(sleep_for)

            if consumer is None:
                yield {
                    "event": "message",
                    "data": json.dumps(
                        {
                            "feed_event": "unavailable",
                            "bootstrap": BOOTSTRAP,
                            "hint": "Start brokers from repo root: docker compose up -d zookeeper kafka",
                        }
                    ),
                }
                return

            yield {
                "event": "message",
                "data": json.dumps({"feed_event": "ready", "topic": CAT_TOPIC}),
            }

            try:
                async for msg in consumer:
                    yield {"event": "message", "data": json.dumps(msg.value)}
            finally:
                try:
                    await consumer.stop()
                except Exception:
                    pass
        finally:
            active_sse_feeds.dec()

    return EventSourceResponse(gen())


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    name = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 20MB limit")
    upload_bytes_total.inc(len(content))

    async def proxy():
        # stream=True so parser SSE chunks reach the browser immediately (same pattern as /coach/*)
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                files = {"file": (name, content, content_type)}
                async with client.stream(
                    "POST",
                    f"{PARSER_URL}/parse",
                    files=files,
                ) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except httpx.ConnectError:
            payload = {
                "step": "error",
                "label": f"Parser service unreachable at {PARSER_URL}. Start parser-service and retry.",
                "done": 0,
                "total": 0,
            }
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
        except httpx.HTTPStatusError as exc:
            payload = {
                "step": "error",
                "label": f"Parser service error: {exc.response.status_code}",
                "done": 0,
                "total": 0,
            }
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")

    return StreamingResponse(
        proxy(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/correct")
async def correct(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{ML_URL}/correct", json=body, timeout=60.0)
        return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/retrain")
async def retrain():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{ML_URL}/retrain", timeout=600.0)
        return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/model-info")
async def model_info():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{ML_URL}/model-info", timeout=30.0)
        return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/coach/stream")
async def coach_stream(request: Request):
    body = await request.json()

    async def gen():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST", f"{GENAI_URL}/coach/stream", json=body
                ) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except httpx.ConnectError:
            payload = {"token": f"[Gateway] GenAI service unreachable at {GENAI_URL}."}
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            yield f"data: {json.dumps({'done': True})}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/coach/monthly")
async def coach_monthly(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GENAI_URL}/coach/monthly", json=body, timeout=120.0)
        return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/coach/monthly/stream")
async def coach_monthly_stream(request: Request):
    body = await request.json()

    async def gen():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST", f"{GENAI_URL}/coach/monthly/stream", json=body
                ) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except httpx.ConnectError:
            payload = {"token": f"[Gateway] GenAI service unreachable at {GENAI_URL}."}
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            yield f"data: {json.dumps({'done': True})}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/coach/statement")
async def coach_statement(request: Request):
    body = await request.json()

    async def gen():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST", f"{GENAI_URL}/coach/statement", json=body
                ) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except httpx.ConnectError:
            payload = {"token": f"[Gateway] GenAI service unreachable at {GENAI_URL}."}
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")
            yield f"data: {json.dumps({'done': True})}\n\n".encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/classify")
async def classify_proxy(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{ML_URL}/classify", json=body, timeout=120.0)
        return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/classify_batch")
async def classify_batch_proxy(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{ML_URL}/classify_batch", json=body, timeout=600.0)
        return JSONResponse(r.json(), status_code=r.status_code)
