"""Raw row -> canonical transaction dict."""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from model_merchant import clean_merchant


def _parse_amount(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def _norm_date(val) -> str:
    if val is None:
        return datetime.utcnow().strftime("%Y-%m-%d")
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.utcnow().strftime("%Y-%m-%d")


def normalise_row(
    row: dict,
    source_file: str,
    currency: str = "INR",
) -> dict:
    merchant_raw = str(
        row.get("description")
        or row.get("narration")
        or row.get("details")
        or row.get("merchant")
        or row.get("particulars")
        or "",
    )
    amt = _parse_amount(row.get("amount") or row.get("debit") or row.get("withdrawal"))
    if amt == 0:
        amt = abs(_parse_amount(row.get("credit") or row.get("deposit")))
    dc = str(row.get("type") or row.get("dr_cr") or "debit").lower()
    if "cr" in dc or "credit" in dc:
        debit_credit = "credit"
    else:
        debit_credit = "debit"

    mc = clean_merchant(merchant_raw)
    return {
        "txn_id": str(uuid.uuid4()),
        "date": _norm_date(row.get("date") or row.get("txn_date")),
        "amount": float(abs(amt)),
        "debit_credit": debit_credit,
        "merchant_raw": merchant_raw or mc,
        "merchant_clean": mc or "Unknown",
        "description": merchant_raw,
        "source": "statement_upload",
        "source_file": source_file,
        "currency": currency,
    }
