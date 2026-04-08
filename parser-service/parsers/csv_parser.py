from __future__ import annotations

import io
from typing import Any

import pandas as pd


def parse_csv(content: bytes, filename: str) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig", errors="replace")
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
    df.columns = [str(c).strip().lower().replace("_", " ") for c in df.columns]
    # Heuristic column rename (bank CSV headers vary widely)
    colmap = {}
    for c in df.columns:
        if c in (
            "date",
            "txn date",
            "transaction date",
            "value date",
            "posting date",
            "tran date",
            "book date",
        ):
            colmap[c] = "date"
        elif c in (
            "description",
            "narration",
            "particulars",
            "details",
            "remarks",
            "payee",
            "merchant",
            "counterparty",
            "txn description",
        ):
            colmap[c] = "description"
        elif c in ("amount", "amt"):
            colmap[c] = "amount"
        elif c in ("withdrawal", "debit", "dr", "dr amount"):
            colmap[c] = "withdrawal"
        elif c in ("deposit", "credit", "cr", "cr amount"):
            colmap[c] = "deposit"
    df = df.rename(columns=colmap)
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(r.to_dict())
    return rows
