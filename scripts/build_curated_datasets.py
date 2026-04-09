"""
Build curated training/evaluation datasets from mixed sources.

Usage:
  python scripts/build_curated_datasets.py \
    --real data/raw/public_real_transactions.csv \
    --synthetic data/transactions_train.csv \
    --out-train data/transactions_train_curated.csv \
    --out-gold data/transactions_gold_eval.csv \
    --gold-size 300

Optional inter-rater agreement:
  python scripts/build_curated_datasets.py ... \
    --dual-label data/raw/gold_double_labeled.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

REQUIRED = ["merchant_raw", "description", "amount", "category"]


def _validate_columns(df: pd.DataFrame, label: str) -> None:
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise ValueError(f"{label} is missing required columns: {miss}")


def _clean(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = df.copy()
    out["merchant_raw"] = out["merchant_raw"].fillna("").astype(str).str.strip()
    out["description"] = out["description"].fillna("").astype(str).str.strip()
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0).astype(float)
    out["category"] = out["category"].fillna("").astype(str).str.strip().str.lower()
    out["source"] = source
    out = out[out["merchant_raw"] != ""]
    out = out.drop_duplicates(subset=["merchant_raw", "description", "amount", "category"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True, help="CSV with real/public rows")
    ap.add_argument("--synthetic", required=True, help="CSV with synthetic rows")
    ap.add_argument("--out-train", default="data/transactions_train_curated.csv")
    ap.add_argument("--out-gold", default="data/transactions_gold_eval.csv")
    ap.add_argument("--gold-size", type=int, default=300)
    ap.add_argument("--dual-label", default="", help="CSV with columns label_a,label_b for IAA")
    ap.add_argument("--summary-json", default="data/data_collection_summary.json")
    args = ap.parse_args()

    real_df = pd.read_csv(args.real)
    syn_df = pd.read_csv(args.synthetic)
    _validate_columns(real_df, "real")
    _validate_columns(syn_df, "synthetic")

    real = _clean(real_df, "public_real")
    syn = _clean(syn_df, "synthetic")
    merged = pd.concat([real, syn], ignore_index=True)
    merged = merged.drop_duplicates(subset=["merchant_raw", "description", "amount", "category"])

    gold_size = max(50, int(args.gold_size))
    gold = merged.sample(n=min(gold_size, len(merged)), random_state=42).copy()
    train = merged.drop(index=gold.index).copy()

    out_train = Path(args.out_train)
    out_gold = Path(args.out_gold)
    out_train.parent.mkdir(parents=True, exist_ok=True)
    out_gold.parent.mkdir(parents=True, exist_ok=True)
    train.to_csv(out_train, index=False)
    gold.to_csv(out_gold, index=False)

    iaa = None
    if args.dual_label:
        dl = pd.read_csv(args.dual_label)
        if {"label_a", "label_b"}.issubset(dl.columns):
            iaa = float(cohen_kappa_score(dl["label_a"], dl["label_b"]))

    summary = {
        "train_rows": int(len(train)),
        "gold_rows": int(len(gold)),
        "real_rows_used": int(len(real)),
        "synthetic_rows_used": int(len(syn)),
        "class_distribution_train": train["category"].value_counts().to_dict(),
        "inter_rater_cohen_kappa": iaa,
        "notes": "gold set is held out from training by construction",
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
