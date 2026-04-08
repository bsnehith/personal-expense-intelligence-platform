"""PDF statements: pdfplumber text + table extraction, PyMuPDF fallback, OCR for scans."""
from __future__ import annotations

import io
import os
import re
from typing import Any

import pdfplumber

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from ocr import ocr_image_bytes

# Dates common on Indian / international statements
_DATE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
)
_DATE_DOT = re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{2,4})\b")
_DATE_MONTH = re.compile(
    r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})\b"
)
_DATE_MON_DASH = re.compile(
    r"\b(\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{2,4}|[A-Za-z]{3,9}[-/]\d{1,2}[-/]\d{2,4})\b"
)
# Years to ignore when treating a number as money
_YEAR_LIKE = {float(y) for y in range(1990, 2036)}
_META_HINTS = (
    "statement summary",
    "statement from",
    "date of statement",
    "account open date",
    "account status",
    "ifsc code",
    "micr code",
    "branch code",
    "branch name",
    "branch email",
    "branch phone",
    "cif number",
    "account number",
    "product",
    "currency",
    "nominee",
    "brought forward",
    "clear balance",
)
_TXN_HINTS = ("upi/", "wdl tfr", "dep tfr", "pos ", "imps", "neft", "atm")


def _candidate_amount_strings(segment: str) -> list[tuple[str, float]]:
    """Money-like tokens in `segment` (usually the line after the date is removed)."""
    out: list[tuple[str, float]] = []
    for m in re.finditer(
        r"(?:₹|Rs\.?|INR\s*)?\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+\.\d{1,2}|\d{2,})\b",
        segment,
        flags=re.I,
    ):
        raw = m.group(1).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        if v <= 0:
            continue
        if v in _YEAR_LIKE and "." not in raw:
            continue
        if v > 99_000_000:
            continue
        out.append((m.group(1), v))
    return out


def _pick_amount_after_date(line: str, date_m: re.Match[str]) -> tuple[str, str] | None:
    """Amounts are matched only in text *outside* the date span to avoid DD/MM noise."""
    rest = line[: date_m.start()] + line[date_m.end() :]
    cands = _candidate_amount_strings(rest)
    if not cands:
        return None
    raw_s, _v = cands[-1]
    return raw_s, raw_s.replace(",", "")


def _extract_date(line: str) -> tuple[str, re.Match[str]] | None:
    for rx in (_DATE, _DATE_DOT, _DATE_MONTH, _DATE_MON_DASH):
        m = rx.search(line)
        if m:
            return m.group(1), m
    return None


def _line_to_row(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line or len(line) < 6:
        return None
    low = line.lower()
    if any(h in low for h in _META_HINTS) and not any(h in low for h in _TXN_HINTS):
        return None
    date_hit = _extract_date(line)
    if not date_hit:
        return None
    date_s, dm = date_hit
    picked = _pick_amount_after_date(line, dm)
    if not picked:
        return None
    amt_display, amt_norm = picked
    # Description ≈ full line minus date and the chosen amount substring
    desc = line.replace(date_s, " ", 1)
    desc = desc.replace(amt_display, " ", 1)
    desc = re.sub(r"\s+", " ", desc).strip(" ₹RsINR,.")
    if not desc:
        desc = line
    return {
        "date": date_s,
        "description": desc or line,
        "amount": amt_norm,
    }


def _amount_float(row: dict[str, Any]) -> float:
    try:
        return float(str(row.get("amount", "0")).replace(",", "").strip())
    except Exception:
        return 0.0


def _row_quality(row: dict[str, Any]) -> int:
    desc = str(row.get("description") or "").strip()
    low = desc.lower()
    amt = _amount_float(row)
    score = 0
    if any(h in low for h in _TXN_HINTS):
        score += 4
    if "upi/" in low:
        score += 4
    if any(h in low for h in _META_HINTS) and not any(h in low for h in _TXN_HINTS):
        score -= 5
    if re.fullmatch(r"[0-9/\-.\s:]+", desc):
        score -= 4
    if amt >= 10:
        score += 1
    if amt <= 5 and not any(h in low for h in _TXN_HINTS):
        score -= 2
    if re.search(r"[a-zA-Z]{3,}", desc):
        score += 1
    return score


def _sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for r in rows:
        q = _row_quality(r)
        if q < 1:
            continue
        key = (
            str(r.get("date") or "").strip(),
            str(r.get("description") or "").strip().lower(),
            str(r.get("amount") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _rows_strength(rows: list[dict[str, Any]]) -> tuple[int, int]:
    # (quality score sum, row count)
    if not rows:
        return (0, 0)
    score = sum(max(0, _row_quality(r)) for r in rows)
    return (score, len(rows))


def _ocr_page_indices(total_pages: int, max_pages: int) -> list[int]:
    """
    Pick OCR pages across the whole statement, not only page-0..N.
    Many bank PDFs place transactions after front-matter pages.
    """
    if total_pages <= 0 or max_pages <= 0:
        return []
    max_pages = min(total_pages, max_pages)
    if total_pages <= max_pages:
        return list(range(total_pages))
    # Always include early pages + evenly spaced coverage.
    picks = {0, 1, 2, total_pages - 1}
    step = max(1, total_pages // max_pages)
    for i in range(0, total_pages, step):
        picks.add(i)
        if len(picks) >= max_pages:
            break
    return sorted(picks)[:max_pages]


def _lines_to_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    n = len(raw_lines)
    for i, line in enumerate(raw_lines):
        r = _line_to_row(line)
        if r:
            rows.append(r)
            continue
        # Common bank/PDF pattern: date/description in one line, amount in next line.
        if i + 1 < n:
            merged = f"{line} {raw_lines[i + 1]}"
            r2 = _line_to_row(merged)
            if r2:
                rows.append(r2)
                continue
        if i + 2 < n:
            merged2 = f"{line} {raw_lines[i + 1]} {raw_lines[i + 2]}"
            r3 = _line_to_row(merged2)
            if r3:
                rows.append(r3)
    return rows


def _as_clean_cells(row: list[Any]) -> list[str]:
    return [str(c or "").strip() for c in row if c is not None and str(c).strip()]


def _header_map(cells: list[str]) -> dict[str, int]:
    h: dict[str, int] = {}
    low = [c.lower() for c in cells]
    for i, c in enumerate(low):
        if "date" in c and "date" not in h:
            h["date"] = i
        if any(k in c for k in ("narrat", "description", "particular", "remark", "details")) and "desc" not in h:
            h["desc"] = i
        if any(k in c for k in ("withdraw", "debit", "dr")) and "debit" not in h:
            h["debit"] = i
        if any(k in c for k in ("deposit", "credit", "cr")) and "credit" not in h:
            h["credit"] = i
        if "amount" in c and "amount" not in h:
            h["amount"] = i
    return h


def _parse_table_row(cells: list[str], hdr: dict[str, int]) -> dict[str, Any] | None:
    if not cells:
        return None
    date_s = ""
    if "date" in hdr and hdr["date"] < len(cells):
        date_s = cells[hdr["date"]]
    if not date_s:
        hit = _extract_date(" ".join(cells))
        if hit:
            date_s = hit[0]
    if not date_s:
        return None

    desc = ""
    if "desc" in hdr and hdr["desc"] < len(cells):
        desc = cells[hdr["desc"]]
    if not desc:
        desc_parts = [
            c
            for idx, c in enumerate(cells)
            if idx not in {hdr.get("date", -1), hdr.get("debit", -1), hdr.get("credit", -1), hdr.get("amount", -1)}
        ]
        desc = " ".join(desc_parts).strip()
    if not desc:
        desc = " ".join(cells)

    amount_src = ""
    for key in ("amount", "debit", "credit"):
        idx = hdr.get(key, -1)
        if 0 <= idx < len(cells):
            cands = _candidate_amount_strings(cells[idx])
            if cands:
                amount_src = cands[-1][0]
                break
    if not amount_src:
        for c in reversed(cells):
            cands = _candidate_amount_strings(c)
            if cands:
                amount_src = cands[0][0]
                break
    if not amount_src:
        return None
    return {"date": date_s, "description": desc, "amount": amount_src.replace(",", "")}


def _guess_statement_date(text: str) -> str:
    """
    Best-effort fallback date for OCR-heavy rows lacking a clean per-row date.
    Prefer 'Statement From : dd-mm-yyyy', else first date in document.
    """
    m = re.search(
        r"statement\s+from\s*:?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
        text,
        flags=re.I,
    )
    if m:
        return m.group(1)
    hit = _extract_date(text)
    return hit[0] if hit else "1970-01-01"


def _extract_upi_rows(text: str) -> list[dict[str, Any]]:
    """
    OCR-oriented extractor for SBI-style UPI ledger lines, e.g.
    'WDL TFR UPI/DR/... ... 130.00' possibly wrapped across 2 lines.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows: list[dict[str, Any]] = []
    cur_date = _guess_statement_date(text)
    i = 0
    while i < len(lines):
        line = lines[i]
        date_hit = _extract_date(line)
        if date_hit:
            cur_date = date_hit[0]
        low = line.lower()
        if any(h in low for h in ("statement from", "details ref", "date of statement")) and "upi/" not in low:
            i += 1
            continue
        if "upi/" not in low and "wdl tfr" not in low and "dep tfr" not in low:
            i += 1
            continue

        merged = line
        j = i + 1
        # Join wrapped continuation lines until we see an amount token.
        while j < len(lines):
            amount_hit = re.search(r"\b(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})|\d+\.\d{1,2})\s*$", merged)
            if amount_hit:
                break
            nxt = lines[j]
            # Stop if a new transaction begins.
            if ("upi/" in nxt.lower() or "wdl tfr" in nxt.lower() or "dep tfr" in nxt.lower()) and len(merged) > len(line):
                break
            merged = f"{merged} {nxt}"
            j += 1

        amount_match = re.search(r"\b(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})|\d+\.\d{1,2})\s*$", merged)
        if amount_match:
            amt = amount_match.group(1).replace(",", "")
            # Strip ATM/terminal tail noise while retaining merchant narrative.
            desc = re.sub(r"\s+\d{10,}\s+AT\s+\d{3,}\s+[A-Z ]+$", "", merged).strip()
            if len(desc) >= 8:
                rows.append({"date": cur_date, "description": desc, "amount": amt})
            i = max(j, i + 1)
            continue

        i += 1
    return rows


def _extract_tables_pdfplumber(content: bytes) -> list[dict[str, Any]]:
    """Many bank PDFs expose transactions as tables, not plain text lines."""
    out: list[dict[str, Any]] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    hdr: dict[str, int] = {}
                    for row in table:
                        if not row:
                            continue
                        cells = _as_clean_cells(row)
                        if not cells:
                            continue
                        if not hdr:
                            maybe = _header_map(cells)
                            if "date" in maybe and len(maybe) >= 2:
                                hdr = maybe
                                continue
                        if hdr:
                            parsed = _parse_table_row(cells, hdr)
                            if parsed:
                                out.append(parsed)
                                continue
                        line = " ".join(cells)
                        if len(line) < 6:
                            continue
                        r = _line_to_row(line)
                        if r:
                            out.append(r)
    except Exception:
        return out
    return out


def _extract_pdfplumber(content: bytes) -> str:
    parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
    except Exception:
        return ""
    return "\n".join(parts)


def _extract_pymupdf(content: bytes) -> str:
    if fitz is None:
        return ""
    parts: list[str] = []
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        for i in range(len(doc)):
            parts.append(doc.load_page(i).get_text("text") or "")
        doc.close()
    except Exception:
        return ""
    return "\n".join(parts)


def parse_pdf(content: bytes, filename: str) -> list[dict[str, Any]]:
    text = _extract_pdfplumber(content)
    rows_from_text = _sanitize_rows(_lines_to_rows(text)) if text else []
    rows_from_tables = _sanitize_rows(_extract_tables_pdfplumber(content))
    rows_from_upi = _sanitize_rows(_extract_upi_rows(text)) if text else []

    candidates = [rows_from_upi, rows_from_tables, rows_from_text]
    base = max(candidates, key=_rows_strength) if any(candidates) else []

    if _rows_strength(base)[0] < 8:
        text2 = _extract_pymupdf(content)
        alt = _sanitize_rows(_lines_to_rows(text2))
        alt_upi = _sanitize_rows(_extract_upi_rows(text2))
        base = max([base, alt_upi, alt], key=_rows_strength)

    # Scanned PDF: little selectable text — raster + OCR (capped for latency)
    max_ocr = int(os.environ.get("OCR_MAX_PAGES", "12"))
    ocr_dpi = int(os.environ.get("OCR_DPI", "170"))
    min_ocr_rows = int(os.environ.get("OCR_MIN_ROWS", "2"))
    if _rows_strength(base)[0] < 8 and fitz is not None:
        doc = fitz.open(stream=content, filetype="pdf")
        page_idxs = _ocr_page_indices(len(doc), max(0, max_ocr))
        ocr_chunks: list[str] = []
        for i in page_idxs:
            page = doc.load_page(int(i))
            mat = fitz.Matrix(ocr_dpi / 72, ocr_dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            ocr_chunks.append(ocr_image_bytes(pix.tobytes("png")))
            # Early stop: once OCR has enough parseable rows, avoid extra expensive pages.
            if len(_sanitize_rows(_lines_to_rows("\n".join(ocr_chunks)))) >= min_ocr_rows:
                break
        doc.close()
        ocr_rows = _sanitize_rows(_lines_to_rows("\n".join(ocr_chunks)))
        ocr_upi_rows = _sanitize_rows(_extract_upi_rows("\n".join(ocr_chunks)))
        base = max([base, ocr_upi_rows, ocr_rows], key=_rows_strength)

    return base
