"""
Generate 3000+ labelled rows for ML training (synthetic + reproducible).
Run: python scripts/generate_training_data.py
Writes: data/transactions_train.csv
"""
from __future__ import annotations

import csv
import os
import random
import sys
import uuid
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "simulator"))
from templates import (  # noqa: E402
    BASE_AMOUNTS,
    TEMPLATES,
    build_merchant_raw,
)

OUT = os.path.join(ROOT, "data", "transactions_train.csv")

# Ensure reproducibility
random.seed(42)


def row_for_category(cat: str) -> dict:
    low, high = BASE_AMOUNTS[cat]
    amount = round(random.uniform(low, high), 2)
    merchant_raw = build_merchant_raw(cat)
    text = f"{merchant_raw} | amt={amount}"
    return {
        "txn_id": str(uuid.uuid4()),
        "merchant_raw": merchant_raw,
        "description": text,
        "amount": amount,
        "category": cat,
        "source": "synthetic_script",
    }


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cats = list(TEMPLATES.keys())
    rows: list[dict] = []
    # ~280 per category * 12 ≈ 3360
    per_cat = 280
    for cat in cats:
        for _ in range(per_cat):
            rows.append(row_for_category(cat))
    random.shuffle(rows)

    fields = ["txn_id", "merchant_raw", "description", "amount", "category", "source"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
