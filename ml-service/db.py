"""PostgreSQL persistence (optional if DATABASE_URL unset)."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:
    psycopg2 = None


def _url() -> str | None:
    return os.environ.get("DATABASE_URL")


@contextmanager
def connect() -> Iterator[Any]:
    if not _url() or psycopg2 is None:
        yield None
        return
    conn = psycopg2.connect(_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_transaction(payload: dict[str, Any]) -> None:
    with connect() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (txn_id, user_id, payload, category, confidence, source, source_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload.get("txn_id"),
                    payload.get("user_id", "default"),
                    Json(payload),
                    payload.get("category"),
                    payload.get("confidence"),
                    payload.get("source"),
                    payload.get("source_file"),
                ),
            )


def insert_correction(txn_id: str, correct_category: str) -> int:
    """Returns total correction count after insert."""
    with connect() as conn:
        if conn is None:
            return 0
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO corrections (txn_id, correct_category) VALUES (%s, %s)",
                (txn_id, correct_category),
            )
            cur.execute("SELECT COUNT(*) FROM corrections")
            row = cur.fetchone()
            return int(row[0]) if row else 0


def get_transaction_payload(txn_id: str) -> dict[str, Any] | None:
    """Latest row for txn_id (for correction → training row)."""
    with connect() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload FROM transactions
                WHERE txn_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (txn_id,),
            )
            row = cur.fetchone()
            if not row or row[0] is None:
                return None
            p = row[0]
            if isinstance(p, dict):
                return p
            if isinstance(p, str):
                return json.loads(p)
            return None


def correction_count() -> int:
    with connect() as conn:
        if conn is None:
            return 0
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM corrections")
            row = cur.fetchone()
            return int(row[0]) if row else 0


def log_parse_event(filename: str, fmt: str, success: bool, rows: int, latency_ms: float) -> None:
    with connect() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO parse_events (filename, format, success, row_count, latency_ms)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (filename, fmt, success, rows, latency_ms),
            )


def list_recent_transactions(user_id: str = "default", limit: int = 500) -> list[dict[str, Any]]:
    """Recent transaction payloads (newest first) for coach/snapshot endpoints."""
    lim = max(1, min(int(limit), 5000))
    with connect() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload
                FROM transactions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, lim),
            )
            rows = cur.fetchall() or []
    out: list[dict[str, Any]] = []
    for row in rows:
        p = row[0]
        if isinstance(p, dict):
            out.append(p)
        elif isinstance(p, str):
            try:
                out.append(json.loads(p))
            except Exception:
                continue
    return out


def record_anomaly_action(txn_id: str, action: str, note: str | None = None) -> dict[str, Any]:
    with connect() as conn:
        if conn is None:
            return {"ok": True, "stored": False, "txn_id": txn_id, "action": action}
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO anomaly_actions (txn_id, action, note)
                VALUES (%s, %s, %s)
                ON CONFLICT (txn_id)
                DO UPDATE SET action = EXCLUDED.action, note = EXCLUDED.note, updated_at = NOW()
                """,
                (txn_id, action, note),
            )
    return {"ok": True, "stored": True, "txn_id": txn_id, "action": action}
