"""pytesseract + OpenCV — deskew, denoise, multi-pass OCR for scanned PDFs."""
from __future__ import annotations

import os
import re

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


def _to_gray(bgr: np.ndarray) -> np.ndarray:
    if len(bgr.shape) == 2:
        return bgr
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def deskew(gray: np.ndarray) -> np.ndarray:
    if cv2 is None:
        return gray
    coords = np.column_stack(np.where(gray > 0))
    if coords.size < 10:
        return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    (h, w) = gray.shape[:2]
    m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_for_ocr(gray: np.ndarray) -> np.ndarray:
    if cv2 is None:
        return gray
    gray = deskew(gray)
    # Normalize contrast for low-quality scans.
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    # Upscale helps OCR on dense statement fonts.
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    th = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return th


def _ocr_quality(text: str) -> tuple[int, int]:
    low = text.lower()
    txn_hits = sum(low.count(k) for k in ("upi/", "wdl tfr", "dep tfr", "imps", "neft", "pos "))
    amt_hits = len(re.findall(r"\b\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})\b", text))
    # Prefer text with more txn cues and monetary values.
    return (txn_hits, amt_hits)


def ocr_image_bytes(png_bytes: bytes) -> str:
    if cv2 is None or pytesseract is None:
        return ""
    tcmd = os.environ.get("TESSERACT_CMD")
    if tcmd:
        pytesseract.pytesseract.tesseract_cmd = tcmd
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return ""
    gray = _to_gray(img)
    th = preprocess_for_ocr(gray)
    configs = (
        "--oem 3 --psm 6",
        "--oem 3 --psm 4",
        "--oem 3 --psm 11",
    )
    best = ""
    best_q = (0, 0)
    for config in configs:
        try:
            out = pytesseract.image_to_string(th, config=config) or ""
        except Exception:
            out = ""
        q = _ocr_quality(out)
        if q > best_q:
            best = out
            best_q = q
    return best


def ocr_pdf_page_raster(pdf_bytes: bytes, page_index: int, dpi: int = 200) -> str:
    """Render one PDF page via PyMuPDF pixmap → OCR."""
    try:
        import fitz
    except ImportError:
        return ""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_index >= len(doc):
        doc.close()
        return ""
    page = doc.load_page(page_index)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png = pix.tobytes("png")
    doc.close()
    return ocr_image_bytes(png)
