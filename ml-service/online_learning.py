"""Corrections: JSONL + PostgreSQL; stats for model-info; training supplement rows."""
from __future__ import annotations

import csv
import json
import os
import threading
from collections import Counter
from pathlib import Path
from typing import Any

_lock = threading.Lock()

try:
    from db import correction_count as db_correction_count
    from db import insert_correction as db_insert_correction
except ImportError:
    db_insert_correction = None
    db_correction_count = None


def _path() -> Path:
    base = os.environ.get("DATA_DIR", "/app/data")
    Path(base).mkdir(parents=True, exist_ok=True)
    return Path(base) / "corrections.jsonl"


def _count_jsonl() -> int:
    p = _path()
    if not p.exists():
        return 0
    with p.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def append_correction_training_row(correct_category: str, payload: dict[str, Any]) -> None:
    """Append a labelled row for retrain (spec: online learning from corrections)."""
    mr = (payload.get("merchant_raw") or "").strip()
    if not mr:
        return
    base = Path(os.environ.get("DATA_DIR", "/app/data"))
    base.mkdir(parents=True, exist_ok=True)
    p = base / "correction_supplement.csv"
    desc = (payload.get("description") or "").strip()
    try:
        amt = float(payload.get("amount") or 0)
    except (TypeError, ValueError):
        amt = 0.0
    row = {
        "merchant_raw": mr,
        "description": desc or f"{mr} | amt={amt}",
        "amount": amt,
        "category": correct_category,
        "source": "user_correction",
    }
    file_exists = p.exists()
    with _lock:
        with p.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["merchant_raw", "description", "amount", "category", "source"],
            )
            if not file_exists:
                w.writeheader()
            w.writerow(row)


def record_correction(txn_id: str, correct_category: str) -> dict[str, Any]:
    rec = {"txn_id": txn_id, "correct_category": correct_category}
    with _lock:
        p = _path()
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    total = _count_jsonl()
    if db_insert_correction:
        try:
            total = db_insert_correction(txn_id, correct_category)
        except Exception:
            pass
    elif db_correction_count:
        try:
            total = max(total, db_correction_count())
        except Exception:
            pass
    return {"ok": True, "stored": True, "total_corrections": total}


def correction_stats() -> dict[str, Any]:
    by_cat: Counter[str] = Counter()
    total = 0
    p = _path()
    if p.exists():
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                    by_cat[o.get("correct_category", "?")] += 1
                    total += 1
                except json.JSONDecodeError:
                    continue
    if db_correction_count:
        try:
            total = max(total, db_correction_count())
        except Exception:
            pass
    return {"total": total, "by_category": dict(by_cat)}
