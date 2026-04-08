"""Shared cleanup (same idea as ml-service)."""
import re

_UPI = re.compile(r"^UPI/[A-Z]{2}/[0-9]+/", re.I)
_MASK = re.compile(r"/X{3,}.*$")
_POS = re.compile(r"^POS\s+[0-9]{2}:[0-9]{2}\s+", re.I)


def clean_merchant(merchant_raw: str) -> str:
    if not merchant_raw:
        return ""
    s = merchant_raw.strip()
    s = _UPI.sub("", s)
    s = _MASK.sub("", s)
    s = _POS.sub("", s)
    return s[:80].strip() or "Unknown"
