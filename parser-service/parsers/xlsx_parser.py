from __future__ import annotations

import io
import os
import zipfile
from typing import Any

import pandas as pd


def parse_xlsx(content: bytes, filename: str) -> list[dict[str, Any]]:
    lower = os.path.basename(filename or "").lower()
    df = None
    errors: list[str] = []

    # Try engine based on extension first, but fall back to the other engine when
    # users upload files with mismatched extension/content.
    preferred = "xlrd" if lower.endswith(".xls") else "openpyxl"
    engines = [preferred, "xlrd" if preferred == "openpyxl" else "openpyxl"]

    for eng in engines:
        try:
            df = pd.read_excel(io.BytesIO(content), engine=eng)
            break
        except (zipfile.BadZipFile, ValueError, ImportError) as e:
            errors.append(f"{eng}: {e}")
        except Exception as e:
            errors.append(f"{eng}: {e}")

    if df is None:
        # Provide actionable error instead of raw "File is not a zip file".
        raise ValueError(
            "Unable to read Excel file. Please upload a valid .xlsx/.xls file "
            "or export the statement as CSV. Details: " + " | ".join(errors)
        )

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
