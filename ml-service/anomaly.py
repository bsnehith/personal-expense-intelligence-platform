"""Anomaly detection per spec §3.2.4: Z-score 2.5σ, Isolation Forest for user cold-start (<30 txns),
first-time merchant (after brief warm-up so the live stream is not 100% alerts), time-of-day."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest

# Spec: Z-score when enough category history
ZSCORE_THRESHOLD = 2.5
MIN_SAMPLES_ZSCORE = 10

# Spec: Isolation Forest for users with fewer than 30 transactions — calibrated on wide synthetic spend
USER_COLD_START_MAX_TXNS = 30

# First merchant alerts only after a short warm-up (spec wants new-merchant signal; pure cold-start is too noisy on simulators)
MIN_TXNS_BEFORE_NEW_MERCHANT = 12


class AnomalyEngine:
    def __init__(self) -> None:
        self._merchants: dict[str, set[str]] = defaultdict(set)
        self._amounts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._user_txn_count: dict[str, int] = defaultdict(int)
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
        if category == "food_dining" and hour is not None and (hour <= 4 or hour >= 23):
            reasons.append("Food spend at an unusual hour")
            types.append("time_pattern")

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
