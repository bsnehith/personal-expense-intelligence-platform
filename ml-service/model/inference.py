"""Load saved model and predict category + probabilities."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from .categories import CATEGORY_IDS, IDX_TO_ID, REVIEW_THRESHOLD, UNCATEGORISED_THRESHOLD
from .merchant_clean import clean_merchant

_KEYWORD_CATEGORY: list[tuple[str, str]] = [
    ("zomato", "food_dining"),
    ("swiggy", "food_dining"),
    ("zepto", "food_dining"),
    ("tea time", "food_dining"),
    ("cafe", "food_dining"),
    ("uber", "transport"),
    ("ola", "transport"),
    ("rapido", "transport"),
    ("irctc", "travel"),
    ("makemytrip", "travel"),
    ("air india", "travel"),
    ("amazon", "shopping"),
    ("flipkart", "shopping"),
    ("myntra", "shopping"),
    ("reliance digital", "shopping"),
    ("apollo", "health_medical"),
    ("pharmeasy", "health_medical"),
    ("hospital", "health_medical"),
    ("netflix", "entertainment"),
    ("spotify", "entertainment"),
    ("steam", "entertainment"),
    ("rent", "housing"),
    ("home loan", "housing"),
    ("electricity", "housing"),
    ("internet bill", "housing"),
    ("github", "subscriptions"),
    ("google one", "subscriptions"),
    ("gym", "subscriptions"),
]


def _keyword_category(merchant_raw: str, description: str) -> str | None:
    text = f"{merchant_raw} {description}".lower()
    for key, cat in _KEYWORD_CATEGORY:
        if key in text:
            return cat
    return None


class Classifier:
    def __init__(self, artifact_dir: Path):
        self.dir = artifact_dir
        self.model = joblib.load(artifact_dir / "model.joblib")
        meta_path = artifact_dir / "metadata.json"
        self.meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        self.mode = self.meta.get("mode", "tfidf")

    def _text(self, merchant_raw: str, description: str, amount: float) -> str:
        # Use cleaned merchant + free-text description so the model generalises
        # better across noisy bank prefixes (UPI/DR/.../ etc.).
        merchant_clean = clean_merchant(merchant_raw or "")
        return f"{merchant_clean} {description} amt={amount}"

    def predict_proba_labels(self, merchant_raw: str, description: str, amount: float):
        text = self._text(merchant_raw, description or "", float(amount))

        if self.mode == "ensemble":
            m = self.model
            pa = m["tfidf"].predict_proba([text])[0]
            emb = m["encoder"].encode([text], show_progress_bar=False)
            pb = m["clf_emb"].predict_proba(emb)[0]
            stack = np.hstack([pa, pb]).reshape(1, -1)
            proba = m["meta"].predict_proba(stack)[0]
            classes = m["meta"].classes_
        elif self.mode == "tfidf":
            pipe = self.model
            proba = pipe.predict_proba([text])[0]
            classes = pipe.named_steps["clf"].classes_
        else:
            enc = self.model["encoder"]
            clf = self.model["classifier"]
            emb = enc.encode([text], show_progress_bar=False)
            proba = clf.predict_proba(emb)[0]
            classes = clf.classes_

        pairs = sorted(
            (float(proba[j]), int(classes[j])) for j in range(len(classes))
        )
        pairs.sort(reverse=True, key=lambda x: x[0])
        return pairs

    def predict(self, merchant_raw: str, description: str, amount: float):
        pairs = self.predict_proba_labels(merchant_raw, description, amount)
        top_p, top_i = pairs[0]
        cat = IDX_TO_ID[int(top_i)]

        if float(top_p) < UNCATEGORISED_THRESHOLD:
            heuristic = _keyword_category(merchant_raw or "", description or "")
            cat = heuristic or "uncategorised"

        alternatives = [
            {"category": IDX_TO_ID[int(i)], "confidence": float(p)}
            for p, i in pairs[:4]
        ]
        review_required = float(top_p) < REVIEW_THRESHOLD
        return {
            "category": cat,
            "confidence": float(top_p),
            "alternatives": alternatives,
            "review_required": review_required,
        }


def load_classifier(artifact_dir: str | Path) -> Classifier:
    return Classifier(Path(artifact_dir))
