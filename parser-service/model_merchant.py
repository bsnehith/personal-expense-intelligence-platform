"""Shared cleanup (same idea as ml-service)."""
import re

_UPI_HEAD = re.compile(r"^.*?\bUPI/[A-Z]{2}/\d+/", re.I)
_MASK = re.compile(r"/X{3,}.*$")
_POS = re.compile(r"^POS\s+[0-9]{2}:[0-9]{2}\s+", re.I)
_TAIL_AMOUNT = re.compile(r"\s+\d+(?:\.\d{1,2})?$")


def _extract_upi_merchant(s: str) -> str | None:
    hit = re.search(r"\bUPI/[A-Z]{2}/\d+/", s, flags=re.I)
    if not hit:
        return None
    tail = s[hit.end() :].strip()
    if not tail:
        return None
    parts = [p.strip() for p in tail.split("/") if p.strip()]
    if not parts:
        return None
    merchant = _TAIL_AMOUNT.sub("", parts[0]).strip()
    return merchant or None


def clean_merchant(merchant_raw: str) -> str:
    if not merchant_raw:
        return ""
    s = merchant_raw.strip()
    upi_merchant = _extract_upi_merchant(s)
    if upi_merchant:
        s = upi_merchant
    else:
        s = _UPI_HEAD.sub("", s)
        s = _MASK.sub("", s)
        s = _POS.sub("", s)
        s = _TAIL_AMOUNT.sub("", s)
    return s[:80].strip() or "Unknown"
