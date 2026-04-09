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
_warned_no_redis = False
_warned_push_error = False


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
    global _warned_no_redis, _warned_push_error
    r = client()
    if r is None:
        if not _warned_no_redis:
            print(
                "[ml-service] REDIS unavailable — cannot push upload results. "
                "Set REDIS_URL or disable Kafka upload path.",
                file=sys.stderr,
                flush=True,
            )
            _warned_no_redis = True
        return
    key = f"upload:queue:{session_id}"
    try:
        r.rpush(key, json.dumps(payload, default=str))
        r.expire(key, 3600)
    except Exception as exc:
        if not _warned_push_error:
            print(
                f"[ml-service] REDIS push failed ({exc}). Upload queue events are skipped.",
                file=sys.stderr,
                flush=True,
            )
            _warned_push_error = True


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
