"""Redis: upload session queue for unified Kafka path."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

try:
    import redis as redis_lib
except ImportError:
    redis_lib = None

_redis = None


def client():
    global _redis
    if redis_lib is None:
        return None
    url = os.environ.get("REDIS_URL")
    if not url:
        return None
    if _redis is None:
        _redis = redis_lib.Redis.from_url(url, decode_responses=True)
    return _redis


def push_upload_result(session_id: str, payload: dict[str, Any]) -> None:
    r = client()
    if r is None:
        print(
            "[ml-service] REDIS unavailable — cannot push upload result "
            f"(upload_session_id={session_id}). Set REDIS_URL or disable Kafka upload path.",
            file=sys.stderr,
            flush=True,
        )
        return
    key = f"upload:queue:{session_id}"
    r.rpush(key, json.dumps(payload, default=str))
    r.expire(key, 3600)


def blpop_upload(session_id: str, timeout: int = 180) -> dict[str, Any] | None:
    r = client()
    if r is None:
        return None
    key = f"upload:queue:{session_id}"
    item = r.blpop([key], timeout=timeout)
    if not item:
        return None
    _, raw = item
    return json.loads(raw)
