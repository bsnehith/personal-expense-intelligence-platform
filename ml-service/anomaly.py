"""Anomaly detection per spec §3.2.4: Z-score 2.5σ, Isolation Forest for user cold-start (<30 txns),
first-time merchant (after brief warm-up so the live stream is not 100% alerts), time-of-day."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import os
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from zoneinfo import ZoneInfo

# Spec: Z-score when enough category history
ZSCORE_THRESHOLD = 2.5
MIN_SAMPLES_ZSCORE = 10

# Spec: Isolation Forest for users with fewer than 30 transactions — calibrated on wide synthetic spend
USER_COLD_START_MAX_TXNS = 30

# First merchant alerts only after a short warm-up (spec wants new-merchant signal; pure cold-start is too noisy on simulators)
MIN_TXNS_BEFORE_NEW_MERCHANT = 12
MIN_SAMPLES_TIME_PATTERN = 18
ANOMALY_TIMEZONE = os.environ.get("ANOMALY_TIMEZONE", "Asia/Kolkata")


class AnomalyEngine:
    def __init__(self) -> None:
        self._merchants: dict[str, set[str]] = defaultdict(set)
        self._amounts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._hours: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        self._user_txn_count: dict[str, int] = defaultdict(int)
        try:
            self._tz = ZoneInfo(ANOMALY_TIMEZONE)
        except Exception:
            self._tz = ZoneInfo("Asia/Kolkata")
        rng = np.random.RandomState(42)
        # Wide log-normal spend shape so real UPI/POS amounts are not all flagged as outliers
        X = rng.lognormal(mean=5.0, sigma=1.25, size=(2500, 1))
        X2 = np.hstack([X, np.log1p(X)])
        self._iso = IsolationForest(
            n_estimators=120,
            contamination=0.1,
            random_state=42,
        )
        self._iso.fit(X2)

    def _parse_hour(self, ts: str | None) -> int | None:
        if not ts:
            return None
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            # Convert to local/business timezone to avoid UTC-vs-local false positives.
            if t.tzinfo is None:
                t = t.replace(tzinfo=self._tz)
            else:
                t = t.astimezone(self._tz)
            return t.hour
        except Exception:
            return None

    def evaluate(
        self,
        user_id: str,
        category: str,
        amount: float,
        merchant_clean: str,
        timestamp: str | None,
    ) -> dict[str, Any] | None:
        self._user_txn_count[user_id] += 1
        n_user = self._user_txn_count[user_id]

        reasons: list[str] = []
        types: list[str] = []

        m = merchant_clean.strip().lower()
        seen = self._merchants[user_id]
        if m and m not in seen and n_user > MIN_TXNS_BEFORE_NEW_MERCHANT:
            reasons.append("First-time merchant name for you")
            types.append("new_merchant")
        if m:
            seen.add(m)

        hist = self._amounts[user_id][category]
        prev = list(hist)
        if len(prev) >= MIN_SAMPLES_ZSCORE:
            arr = np.array(prev, dtype=float)
            mu, sd = float(arr.mean()), float(arr.std() or 1.0)
            z = (float(amount) - mu) / sd if sd > 0 else 0.0
            if z > ZSCORE_THRESHOLD:
                reasons.append(
                    f"{z:.1f}σ above your recent average in this category ({category})"
                )
                types.append("zscore_amount")

        hist.append(float(amount))
        if len(hist) > 200:
            del hist[:-200]

        hour = self._parse_hour(timestamp)
        hour_hist = self._hours[user_id][category]
        if hour is not None:
            # Rule-based guardrails + personalized hour profile once enough history exists.
            unusual_by_rule = category == "food_dining" and (hour <= 4 or hour >= 23)
            unusual_by_profile = False
            if len(hour_hist) >= MIN_SAMPLES_TIME_PATTERN:
                arr_h = np.array(hour_hist, dtype=float)
                mu_h = float(arr_h.mean())
                sd_h = float(arr_h.std() or 1.0)
                z_h = abs(float(hour) - mu_h) / sd_h if sd_h > 0 else 0.0
                unusual_by_profile = z_h >= 2.5
            if unusual_by_rule or unusual_by_profile:
                reasons.append("Spend at an unusual local hour")
                types.append("time_pattern")
            hour_hist.append(int(hour))
            if len(hour_hist) > 300:
                del hour_hist[:-300]

        # IF only when user is in cold-start AND category lacks Z-score history (spec §3.2.4)
        if n_user <= USER_COLD_START_MAX_TXNS and len(prev) < MIN_SAMPLES_ZSCORE:
            v = np.array([[amount, np.log1p(amount)]], dtype=float)
            if self._iso.predict(v)[0] == -1:
                reasons.append("Amount pattern looks unusual vs typical spending shape")
                types.append("isolation_cold_start")

        if not reasons:
            return None
        return {"reason": "; ".join(reasons[:3]), "types": types}


anomaly_engine = AnomalyEngine()
