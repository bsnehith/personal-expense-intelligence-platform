"""Deterministic string cleanup (regex). Not a classifier."""
import re

_UPI_HEAD = re.compile(r"^.*?\bUPI/[A-Z]{2}/\d+/", re.I)
_MASK = re.compile(r"/X{3,}.*$")
_POS = re.compile(r"^POS\s+[0-9]{2}:[0-9]{2}\s+", re.I)
_TAIL_AMOUNT = re.compile(r"\s+\d+(?:\.\d{1,2})?$")
_EXTRA = re.compile(r"\s+")


def _extract_upi_merchant(s: str) -> str | None:
    """
    Example:
      WDL TFR UPI/DR/609623406929/ZOMATO L/HDFC/zom 273.78
    -> ZOMATO L
    """
    hit = re.search(r"\bUPI/[A-Z]{2}/\d+/", s, flags=re.I)
    if not hit:
        return None
    tail = s[hit.end() :].strip()
    if not tail:
        return None
    parts = [p.strip() for p in tail.split("/") if p.strip()]
    if not parts:
        return None
    merchant = parts[0]
    merchant = _TAIL_AMOUNT.sub("", merchant).strip()
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

    s = re.sub(r"[*]{2,}.*$", "", s)
    s = _EXTRA.sub(" ", s).strip()
    if len(s) > 60:
        s = s[:60].rsplit(" ", 1)[0]
    return s or "unknown"
