"""Synthetic labelled rows for bootstrap training (no external datasets)."""
from __future__ import annotations

import random
import uuid

from .categories import CATEGORY_IDS

_TEMPLATES: dict[str, list[str]] = {
    "food_dining": ["SWIGGY", "ZOMATO", "DOMINOS", "BIGBASKET", "CAFE DAY"],
    "transport": ["UBER", "OLA", "RAPIDO", "SHELL PETROL", "IRCTC"],
    "shopping": ["AMAZON", "FLIPKART", "MYNTRA", "REL DIGITAL"],
    "housing": ["RENT", "BESCOM", "HOME LOAN EMI", "INTERNET BILL"],
    "health_medical": ["APOLLO", "PHARMEASY", "HOSPITAL", "MAX HEALTH"],
    "entertainment": ["NETFLIX", "PVR", "STEAM", "SPOTIFY"],
    "travel": ["MAKEMYTRIP", "AIR INDIA", "AIRBNB"],
    "education": ["UDEMY", "COLLEGE FEE", "STATIONERY"],
    "finance": ["CREDIT CARD", "ZERODHA", "EMI ICICI"],
    "subscriptions": ["GITHUB", "GOOGLE ONE", "GYM"],
    "family_personal": ["NYKAA", "SALON", "CHILD CARE"],
    "uncategorised": ["UNKNOWN MERCHANT", "MISC POS", "UNCODED"],
}


def _one_row(cat: str) -> dict:
    base = random.choice(_TEMPLATES.get(cat, ["GENERIC"]))
    upi = random.randint(100000, 999999)
    merchant_raw = f"UPI/DR/{upi}/{base} INDIA/XXXX"
    amount = round(random.uniform(20, 15000), 2)
    return {
        "txn_id": str(uuid.uuid4()),
        "merchant_raw": merchant_raw,
        "description": f"{merchant_raw} amt={amount}",
        "amount": amount,
        "category": cat,
        "source": "bootstrap_synthetic",
    }


def generate_bootstrap_rows(total: int = 3200) -> list[dict]:
    random.seed(42)
    per = max(total // len(CATEGORY_IDS), 50)
    rows: list[dict] = []
    for cat in CATEGORY_IDS:
        for _ in range(per):
            rows.append(_one_row(cat))
    random.shuffle(rows)
    return rows[:total]
