"""Weighted category distribution + realistic UPI/POS-style templates (not used for ML rules)."""
import random
import uuid
from datetime import datetime, timezone

# Relative frequencies: Food highest, Finance/Travel lowest (spec)
CATEGORY_WEIGHTS = [
    ("food_dining", 22),
    ("transport", 14),
    ("shopping", 14),
    ("housing", 10),
    ("health_medical", 8),
    ("entertainment", 8),
    ("travel", 4),
    ("education", 6),
    ("finance", 4),
    ("subscriptions", 6),
    ("family_personal", 6),
    ("uncategorised", 2),
]

TEMPLATES = {
    "food_dining": [
        "UPI/DR/{upi}/SWIGGY INDIASSW/{mask}",
        "UPI/DR/{upi}/ZOMATO LTD/{mask}",
        "POS 09:14 DOMINOS PIZZA MUMBAI",
        "UPI/CR/{upi}/BIGBASKET/{mask}",
        "NEFT DR BLR CAFE DAY OUTLET",
    ],
    "transport": [
        "UPI/DR/{upi}/UBER INDIA/{mask}",
        "UPI/DR/{upi}/OLA FINANCIAL/{mask}",
        "POS SHELL PETROL BANGALORE",
        "UPI/DR/{upi}/RAPIDO/{mask}",
        "IMPS DR IRCTC TICKET",
    ],
    "shopping": [
        "POS 11:02 AMAZON SELLER*MBF",
        "UPI/DR/{upi}/FLIPKART PAYMENTS/{mask}",
        "UPI/DR/{upi}/MYNTRA DESIGNS/{mask}",
        "POS RELIANCE DIGITAL BLR",
    ],
    "housing": [
        "NEFT RENT PAYMENT LANDLORD",
        "UPI/DR/{upi}/BESCOM BILL/{mask}",
        "ACH DR HOME LOAN EMI HDFC",
        "UPI/DR/{upi}/INTERNET BILL ACT/{mask}",
    ],
    "health_medical": [
        "POS APOLLO PHARMACY",
        "UPI/DR/{upi}/PHARMEASY/{mask}",
        "NEFT DR CITY HOSPITAL",
        "UPI/DR/{upi}/MAX HEALTHCARE/{mask}",
    ],
    "entertainment": [
        "UPI/DR/{upi}/NETFLIX ENTERTAINMENT/{mask}",
        "POS PVR CINEMAS",
        "UPI/DR/{upi}/STEAM PURCHASE/{mask}",
        "UPI/DR/{upi}/SPOTIFY INDIA/{mask}",
    ],
    "travel": [
        "UPI/DR/{upi}/MAKEMYTRIP INDIA/{mask}",
        "POS AIR INDIA AIRPORT",
        "UPI/DR/{upi}/AIRBNB PAYMENTS/{mask}",
    ],
    "education": [
        "POS STATIONERY WORLD",
        "UPI/DR/{upi}/UDEMY INDIA/{mask}",
        "NEFT COLLEGE FEE PAYMENT",
    ],
    "finance": [
        "ACH DR CREDIT CARD PAYMENT",
        "UPI/DR/{upi}/ZERODHA BROKING/{mask}",
        "NEFT EMI ICICI LOAN",
    ],
    "subscriptions": [
        "UPI/DR/{upi}/GITHUB INC/{mask}",
        "UPI/DR/{upi}/GOOGLE STORAGE/{mask}",
        "POS GYM NATION MEMBERSHIP",
    ],
    "family_personal": [
        "UPI/DR/{upi}/NYKAA RETAIL/{mask}",
        "POS SALON SPARKLE",
        "UPI/DR/{upi}/CHILD CARE CENTER/{mask}",
    ],
    "uncategorised": [
        "UPI/DR/{upi}/UNKNOWN MERCHANT/{mask}",
        "POS MISCELLANEOUS TXN",
        "NEFT DR UNCODED BENEFICIARY",
    ],
}

BASE_AMOUNTS = {
    "food_dining": (40, 900),
    "transport": (25, 1200),
    "shopping": (99, 8000),
    "housing": (500, 25000),
    "health_medical": (120, 6000),
    "entertainment": (199, 2500),
    "travel": (800, 45000),
    "education": (500, 12000),
    "finance": (1000, 50000),
    "subscriptions": (49, 2500),
    "family_personal": (150, 7000),
    "uncategorised": (10, 5000),
}


def _pick_category() -> str:
    total = sum(w for _, w in CATEGORY_WEIGHTS)
    r = random.uniform(0, total)
    acc = 0.0
    for cat, w in CATEGORY_WEIGHTS:
        acc += w
        if r <= acc:
            return cat
    return "food_dining"


def _mask() -> str:
    return "X" * random.randint(4, 8)


def _upi() -> str:
    return str(random.randint(100000, 999999))


def build_merchant_raw(category: str) -> str:
    tpl = random.choice(TEMPLATES[category])
    return tpl.format(upi=_upi(), mask=_mask())


def build_transaction(anomaly_every: int = 25) -> dict:
    category = _pick_category()
    low, high = BASE_AMOUNTS[category]
    amount = round(random.uniform(low, high), 2)
    merchant_raw = build_merchant_raw(category)

    # Intentional anomaly: ~1 in anomaly_every is 5x normal for category
    if random.randint(1, anomaly_every) == 1:
        amount = round(amount * 5, 2)

    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    ts = datetime.now(timezone.utc).replace(hour=hour, minute=minute, second=0, microsecond=0)

    return {
        "txn_id": str(uuid.uuid4()),
        "amount": float(amount),
        "merchant_raw": merchant_raw,
        "timestamp": ts.isoformat(),
        "debit_credit": "debit",
        "simulator_category": category,
    }
