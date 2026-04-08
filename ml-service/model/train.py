"""Train TF-IDF, embedding, or stacked ensemble + optional MLflow logging."""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .categories import CATEGORY_IDS, ID_TO_IDX
from .merchant_clean import clean_merchant
from .synthetic_data import generate_bootstrap_rows

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
except Exception:  # pragma: no cover
    mlflow = None


def _load_frame(csv_path: str | None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if csv_path and os.path.isfile(csv_path):
        frames.append(pd.read_csv(csv_path))
    else:
        rows = generate_bootstrap_rows(3200)
        frames.append(pd.DataFrame(rows))
    sup = Path(os.environ.get("DATA_DIR", "data")) / "correction_supplement.csv"
    if sup.is_file():
        try:
            extra = pd.read_csv(sup)
            if len(extra):
                frames.append(extra)
        except Exception:
            pass
    df = pd.concat(frames, ignore_index=True)
    if len(df) and "merchant_raw" in df.columns and "category" in df.columns:
        df = df.drop_duplicates(subset=["merchant_raw", "amount", "category"], keep="last")
    return df


def _build_text(row: pd.Series) -> str:
    merchant_clean = clean_merchant(str(row.get("merchant_raw", "")))
    return f"{merchant_clean} {row.get('description', '')} amt={row['amount']}"


def _resolve_gold_eval_path(explicit: str | None) -> str | None:
    if explicit and os.path.isfile(explicit):
        return explicit
    candidate = os.path.join(os.environ.get("DATA_DIR", "data"), "transactions_gold_eval.csv")
    if os.path.isfile(candidate):
        return candidate
    return None


def _eval_on_gold(model_obj: Any, mode: str, gold_csv: str | None) -> dict[str, Any]:
    if not gold_csv:
        return {}
    try:
        gold = pd.read_csv(gold_csv)
    except Exception:
        return {}
    if not len(gold) or "category" not in gold.columns or "merchant_raw" not in gold.columns:
        return {}
    gold = gold[gold["category"].isin(CATEGORY_IDS)].copy()
    if not len(gold):
        return {}

    texts = gold.apply(_build_text, axis=1).tolist()
    y_true = gold["category"].map(ID_TO_IDX).astype(int).values

    if mode == "ensemble":
        p1 = model_obj["tfidf"].predict_proba(texts)
        emb = model_obj["encoder"].encode(texts, batch_size=64, show_progress_bar=False)
        p2 = model_obj["clf_emb"].predict_proba(emb)
        x_stack = np.hstack([p1, p2])
        y_pred = model_obj["meta"].predict(x_stack)
    elif mode == "tfidf":
        y_pred = model_obj.predict(texts)
    else:
        emb = model_obj["encoder"].encode(texts, batch_size=64, show_progress_bar=False)
        y_pred = model_obj["classifier"].predict(emb)

    return {
        "gold_eval_rows": int(len(gold)),
        "gold_eval_accuracy": float(accuracy_score(y_true, y_pred)),
        "gold_eval_f1_weighted": float(f1_score(y_true, y_pred, average="weighted")),
    }


def train_tfidf(df: pd.DataFrame, random_state: int = 42):
    df = df[df["category"].isin(CATEGORY_IDS)].copy()
    texts = df.apply(_build_text, axis=1).tolist()
    y = df["category"].map(ID_TO_IDX).astype(int).values

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, y, test_size=0.2, random_state=random_state, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, y, test_size=0.2, random_state=random_state
        )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=50000, ngram_range=(1, 2), min_df=1)),
            (
                "clf",
                LogisticRegression(max_iter=2000, class_weight="balanced", solver="saga"),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    pred = pipeline.predict(X_test)
    acc = float(accuracy_score(y_test, pred))
    f1 = float(f1_score(y_test, pred, average="weighted"))
    cm = confusion_matrix(y_test, pred).tolist()
    return pipeline, {"eval_accuracy": acc, "eval_f1_weighted": f1, "mode": "tfidf", "confusion_matrix": cm}


def train_embedding(df: pd.DataFrame, random_state: int = 42):
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers not available")
    df = df[df["category"].isin(CATEGORY_IDS)].copy()
    texts = df.apply(_build_text, axis=1).tolist()
    y = df["category"].map(ID_TO_IDX).astype(int).values

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, y, test_size=0.2, random_state=random_state, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, y, test_size=0.2, random_state=random_state
        )

    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb_train = model.encode(X_train, batch_size=64, show_progress_bar=False)
    emb_test = model.encode(X_test, batch_size=64, show_progress_bar=False)

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")
    clf.fit(emb_train, y_train)
    pred = clf.predict(emb_test)
    acc = float(accuracy_score(y_test, pred))
    f1 = float(f1_score(y_test, pred, average="weighted"))
    cm = confusion_matrix(y_test, pred).tolist()

    bundle = {"encoder": model, "classifier": clf, "scaler": None}
    return bundle, {"eval_accuracy": acc, "eval_f1_weighted": f1, "mode": "embedding", "confusion_matrix": cm}


def train_ensemble(df: pd.DataFrame, random_state: int = 42):
    """Stack TF-IDF + MiniLM probability outputs with a meta logistic regression."""
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers required for ensemble")
    df = df[df["category"].isin(CATEGORY_IDS)].copy()
    texts = df.apply(_build_text, axis=1).tolist()
    y = df["category"].map(ID_TO_IDX).astype(int).values

    try:
        X_train, X_temp, y_train, y_temp = train_test_split(
            texts, y, test_size=0.35, random_state=random_state, stratify=y
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=random_state, stratify=y_temp
        )
    except ValueError:
        X_train, X_temp, y_train, y_temp = train_test_split(
            texts, y, test_size=0.35, random_state=random_state
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=random_state
        )

    tfidf_pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=50000, ngram_range=(1, 2), min_df=1)),
            (
                "clf",
                LogisticRegression(max_iter=2000, class_weight="balanced", solver="saga"),
            ),
        ]
    )
    tfidf_pipe.fit(X_train, y_train)

    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    emb_tr = encoder.encode(X_train, batch_size=64, show_progress_bar=False)
    clf_emb = LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")
    clf_emb.fit(emb_tr, y_train)

    p1_val = tfidf_pipe.predict_proba(X_val)
    p2_val = clf_emb.predict_proba(encoder.encode(X_val, batch_size=64, show_progress_bar=False))
    X_stack_val = np.hstack([p1_val, p2_val])
    meta = LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs")
    meta.fit(X_stack_val, y_val)

    p1_test = tfidf_pipe.predict_proba(X_test)
    p2_test = clf_emb.predict_proba(encoder.encode(X_test, batch_size=64, show_progress_bar=False))
    X_stack_test = np.hstack([p1_test, p2_test])
    pred = meta.predict(X_stack_test)
    acc = float(accuracy_score(y_test, pred))
    f1 = float(f1_score(y_test, pred, average="weighted"))
    cm = confusion_matrix(y_test, pred).tolist()

    bundle = {
        "mode": "ensemble",
        "tfidf": tfidf_pipe,
        "encoder": encoder,
        "clf_emb": clf_emb,
        "meta": meta,
    }
    metrics = {
        "eval_accuracy": acc,
        "eval_f1_weighted": f1,
        "mode": "ensemble",
        "confusion_matrix": cm,
        "version": "2.0.0-ensemble",
    }
    return bundle, metrics


def save_artifacts(out_dir: Path, model_obj, meta: dict, training_rows: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model_obj, out_dir / "model.joblib")

    meta_out = {
        "version": meta.get("version", "1.0.0"),
        "training_rows": training_rows,
        "eval_accuracy": meta.get("eval_accuracy", 0),
        "eval_f1_weighted": meta.get("eval_f1_weighted", 0),
        "mode": meta.get("mode", "tfidf"),
        "categories": CATEGORY_IDS,
        "last_trained_at": datetime.now(timezone.utc).isoformat(),
        "confusion_matrix": meta.get("confusion_matrix", []),
        "gold_eval_rows": meta.get("gold_eval_rows", 0),
        "gold_eval_accuracy": meta.get("gold_eval_accuracy", None),
        "gold_eval_f1_weighted": meta.get("gold_eval_f1_weighted", None),
        "promotion_threshold": meta.get("promotion_threshold", 0.80),
        "promotion_gate_metric": meta.get("promotion_gate_metric", "eval_accuracy"),
        "promoted_to_production": meta.get("promoted_to_production", False),
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta_out, indent=2), encoding="utf-8")


def _mlflow_log(meta: dict, training_rows: int, model_path: Path) -> None:
    if mlflow is None or not os.environ.get("MLFLOW_TRACKING_URI"):
        return
    try:
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment("expense-categorisation")
        with mlflow.start_run(run_name=f"train-{meta.get('mode', 'm')}"):
            threshold = float(os.environ.get("MODEL_PROMOTION_MIN_ACC", "0.80"))
            mlflow.log_params(
                {
                    "mode": meta.get("mode"),
                    "training_rows": training_rows,
                    "promotion_threshold": threshold,
                }
            )
            mlflow.log_metrics(
                {
                    "eval_accuracy": float(meta.get("eval_accuracy", 0)),
                    "eval_f1_weighted": float(meta.get("eval_f1_weighted", 0)),
                }
            )
            if "gold_eval_accuracy" in meta and meta.get("gold_eval_accuracy") is not None:
                mlflow.log_metrics(
                    {
                        "gold_eval_accuracy": float(meta.get("gold_eval_accuracy", 0)),
                        "gold_eval_f1_weighted": float(meta.get("gold_eval_f1_weighted", 0)),
                    }
                )
            if model_path.exists():
                mlflow.log_artifact(str(model_path / "metadata.json"))
                if os.environ.get("MLFLOW_ENABLE_REGISTRY", "1") == "1":
                    model_name = os.environ.get("MLFLOW_MODEL_NAME", "expense-categoriser")
                    model_uri = mlflow.sklearn.log_model(
                        sk_model=joblib.load(model_path / "model.joblib"),
                        artifact_path="model",
                    ).model_uri
                    version = mlflow.register_model(model_uri=model_uri, name=model_name).version
                    if bool(meta.get("promoted_to_production")):
                        MlflowClient().transition_model_version_stage(
                            name=model_name,
                            version=version,
                            stage="Production",
                            archive_existing_versions=True,
                        )
    except Exception:
        pass


def run_training(
    data_csv: str | None,
    out_dir: str,
    use_embedding: bool,
    use_ensemble: bool,
    gold_eval_csv: str | None,
) -> dict:
    random.seed(42)
    np.random.seed(42)
    df = _load_frame(data_csv)
    training_rows = len(df)
    out_path = Path(out_dir)

    if use_ensemble:
        model_obj, metrics = train_ensemble(df)
        meta = {**metrics, "version": metrics.get("version", "2.0.0-ensemble")}
    elif use_embedding:
        model_obj, metrics = train_embedding(df)
        meta = {**metrics, "version": "1.1.0-embedding"}
    else:
        model_obj, metrics = train_tfidf(df)
        meta = {**metrics, "version": "1.0.0-tfidf"}

    gold_metrics = _eval_on_gold(model_obj, meta.get("mode", "tfidf"), gold_eval_csv)
    if gold_metrics:
        meta.update(gold_metrics)
    threshold = float(os.environ.get("MODEL_PROMOTION_MIN_ACC", "0.80"))
    gate_score = float(meta.get("gold_eval_accuracy", meta.get("eval_accuracy", 0)))
    meta["promotion_threshold"] = threshold
    meta["promotion_gate_metric"] = (
        "gold_eval_accuracy" if meta.get("gold_eval_accuracy") is not None else "eval_accuracy"
    )
    meta["promoted_to_production"] = bool(gate_score >= threshold)

    save_artifacts(out_path, model_obj, meta, training_rows)
    _mlflow_log(meta, training_rows, out_path)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="", help="Path to transactions_train.csv")
    ap.add_argument("--out", default=os.environ.get("MODEL_DIR", "model/artifacts"))
    ap.add_argument("--embedding", action="store_true")
    ap.add_argument("--ensemble", action="store_true")
    ap.add_argument("--gold-eval", default="", help="Path to held-out gold evaluation CSV")
    args = ap.parse_args()
    use_emb = bool(args.embedding) or os.environ.get("USE_EMBEDDING_MODEL") == "1"
    use_ens = bool(args.ensemble) or os.environ.get("USE_ENSEMBLE") == "1"
    default_csv = os.path.join(os.environ.get("DATA_DIR", "data"), "transactions_train.csv")
    csv_path = None
    if args.data and os.path.isfile(args.data):
        csv_path = args.data
    elif os.path.isfile(default_csv):
        csv_path = default_csv
    if use_ens:
        use_emb = False
    gold_eval = _resolve_gold_eval_path(args.gold_eval or None)
    meta = run_training(csv_path, args.out, use_emb, use_ens, gold_eval)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
