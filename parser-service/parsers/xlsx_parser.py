from __future__ import annotations

import io
import os
from typing import Any

import pandas as pd


def parse_xlsx(content: bytes, filename: str) -> list[dict[str, Any]]:
    lower = os.path.basename(filename or "").lower()
    if lower.endswith(".xls"):
        # Legacy Excel requires xlrd engine.
        df = pd.read_excel(io.BytesIO(content), engine="xlrd")
    else:
        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    df.columns = [str(c).strip().lower() for c in df.columns]
    colmap = {}
    for c in df.columns:
        if "date" in c:
            colmap[c] = "date"
        elif any(x in c for x in ("desc", "narrat", "detail", "particular")):
            colmap[c] = "description"
        elif "amount" in c or "amt" in c or "withdraw" in c or "deposit" in c:
            colmap[c] = "amount"
    df = df.rename(columns=colmap)
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rows.append(r.to_dict())
    return rows
