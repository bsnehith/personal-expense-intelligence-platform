"""Gemini streaming + deterministic fallback."""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import time
from pathlib import Path
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from metrics import genai_coach_first_token_ms, genai_coach_invocations
from prompts import chat_prompt, monthly_prompt, statement_summary_prompt

try:
    from google import genai
except ImportError:  # pragma: no cover
    genai = None

# Local uvicorn runs don't source docker-compose .env automatically.
# Load service-level .env first, then repo-root .env as fallback.
_SERVICE_ROOT = Path(__file__).resolve().parent
load_dotenv(_SERVICE_ROOT / ".env", override=False)
load_dotenv(_SERVICE_ROOT.parent / ".env", override=False)

_RETRY_ATTEMPTS = max(1, int(os.environ.get("GEMINI_RETRY_ATTEMPTS", "3")))
_RETRY_BASE_DELAY_SEC = max(0.2, float(os.environ.get("GEMINI_RETRY_BASE_DELAY_SEC", "1.0")))


def _client():
    if genai is None:
        return None
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)


def _gen_config() -> dict[str, float | int]:
    return {
        "temperature": float(os.environ.get("GEMINI_TEMPERATURE", "0.35")),
        "top_p": float(os.environ.get("GEMINI_TOP_P", "0.9")),
        "top_k": int(os.environ.get("GEMINI_TOP_K", "40")),
    }


def _is_greeting(question: str) -> bool:
    q = (question or "").strip().lower()
    return q in {
        "hi",
        "hii",
        "hello",
        "hey",
        "yo",
        "good morning",
        "good afternoon",
        "good evening",
    }


def _is_transient_genai_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    hints = (
        "503",
        "unavailable",
        "high demand",
        "resource_exhausted",
        "429",
        "rate",
        "try again later",
    )
    return any(h in msg for h in hints)


async def _stream_via_gemini(client, model: str, text: str) -> AsyncIterator[str]:
    stream_cm = client.aio.models.generate_content_stream(
        model=model,
        contents=text,
        config=_gen_config(),
    )
    stream = await stream_cm if inspect.isawaitable(stream_cm) else stream_cm
    async for chunk in stream:
        tok = getattr(chunk, "text", None)
        if tok:
            yield tok


async def stream_chat(question: str, transactions: list) -> AsyncIterator[str]:
    genai_coach_invocations.labels(endpoint="stream").inc()
    if _is_greeting(question):
        # Deterministic short opener per UX request: brief greeting + one follow-up question.
        msg = (
            "Hi. I can help with your spending insights. "
            "Do you want a quick summary or a category-wise analysis?"
        )
        for i in range(0, len(msg), 26):
            yield msg[i : i + 26]
        return

    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    client = _client()
    text = chat_prompt(question, transactions)
    first = True
    t0 = time.perf_counter()
    if client is None:
        for chunk in _fallback_stream(text):
            if first:
                genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
                first = False
            yield chunk
        return
    last_error: Exception | None = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            async for t in _stream_via_gemini(client, model, text):
                if first:
                    genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
                    first = False
                yield t
            return
        except Exception as e:
            last_error = e
            if _is_transient_genai_error(e) and attempt < _RETRY_ATTEMPTS:
                await asyncio.sleep(_RETRY_BASE_DELAY_SEC * attempt)
                continue
            break

    # Graceful fallback for temporary provider outages; avoid leaking raw stack/error JSON to UI.
    if first:
        genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
    fallback_msg = (
        "The AI coach is temporarily busy right now. "
        "I can still help with a quick rule-based summary, or you can retry in a minute."
    )
    for i in range(0, len(fallback_msg), 24):
        yield fallback_msg[i : i + 24]
    if last_error and not _is_transient_genai_error(last_error):
        yield " (non-transient provider error)"


async def stream_statement_summary(
    transactions: list[dict[str, Any]], source_file: str = ""
) -> AsyncIterator[str]:
    """Stream the five mandated insight sections for a completed statement upload."""
    genai_coach_invocations.labels(endpoint="statement").inc()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    client = _client()
    text = statement_summary_prompt(transactions, source_file)
    first = True
    t0 = time.perf_counter()
    if client is None:
        for chunk in _fallback_stream(text):
            if first:
                genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
                first = False
            yield chunk
        return
    last_error: Exception | None = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            async for t in _stream_via_gemini(client, model, text):
                if first:
                    genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
                    first = False
                yield t
            return
        except Exception as e:
            last_error = e
            if _is_transient_genai_error(e) and attempt < _RETRY_ATTEMPTS:
                await asyncio.sleep(_RETRY_BASE_DELAY_SEC * attempt)
                continue
            break

    if first:
        genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
    # Statement-specific fallback keeps UX useful when provider is overloaded.
    total = sum(float(t.get("amount") or 0) for t in transactions)
    msg = (
        f"[Temporary AI provider overload] Parsed {len(transactions)} transactions from "
        f"{source_file or 'your statement'} with approx ₹{total:,.0f} total spend. "
        "Please retry in 1-2 minutes for full GenAI insights."
    )
    for i in range(0, len(msg), 26):
        yield msg[i : i + 26]
    if last_error and not _is_transient_genai_error(last_error):
        yield " (non-transient provider error)"


async def stream_monthly_summary(
    transactions: list[dict[str, Any]],
) -> AsyncIterator[str]:
    """Stream monthly review tokens (same sections as monthly_json)."""
    genai_coach_invocations.labels(endpoint="monthly_stream").inc()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    client = _client()
    text = monthly_prompt(transactions)
    first = True
    t0 = time.perf_counter()
    if client is None:
        for chunk in _fallback_stream(text):
            if first:
                genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
                first = False
            yield chunk
        return
    last_error: Exception | None = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            async for t in _stream_via_gemini(client, model, text):
                if first:
                    genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
                    first = False
                yield t
            return
        except Exception as e:
            last_error = e
            if _is_transient_genai_error(e) and attempt < _RETRY_ATTEMPTS:
                await asyncio.sleep(_RETRY_BASE_DELAY_SEC * attempt)
                continue
            break

    if first:
        genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
    fallback = _fallback_monthly(transactions)
    for i in range(0, len(fallback), 24):
        yield fallback[i : i + 24]
    if last_error and not _is_transient_genai_error(last_error):
        yield " (non-transient provider error)"


async def monthly_json(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    genai_coach_invocations.labels(endpoint="monthly").inc()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
    client = _client()
    prompt = monthly_prompt(transactions)
    t0 = time.perf_counter()
    if client is None:
        genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
        return {"text": _fallback_monthly(transactions), "error": None}
    try:
        resp = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=_gen_config(),
        )
        genai_coach_first_token_ms.observe((time.perf_counter() - t0) * 1000)
        out = getattr(resp, "text", None) or str(resp)
        return {"text": out, "error": None}
    except Exception as e:
        return {"text": _fallback_monthly(transactions), "error": str(e)}


def _fallback_stream(_text: str):
    msg = (
        "[Demo mode — set GEMINI_API_KEY] "
        "GenAI coach is running without Gemini credentials. "
        "Set GEMINI_API_KEY in .env and restart genai-service."
    )
    for i in range(0, len(msg), 24):
        yield msg[i : i + 24]


def _fallback_monthly(transactions: list) -> str:
    total = sum(float(t.get("amount") or 0) for t in transactions)
    return (
        f"[Demo mode — set GEMINI_API_KEY] Monthly snapshot: ~{len(transactions)} txns, "
        f"approx ₹{total:,.0f} total spend. Review top merchants and recurring charges."
    )
