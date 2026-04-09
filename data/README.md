# Curated Data Workspace

This folder stores project datasets used by the ML training pipeline.

## Expected files

- `transactions_train.csv` - training dataset (>= 3000 rows target)
- `transactions_gold_eval.csv` - held-out gold evaluation set (target 300 rows; never train on it)
- `correction_supplement.csv` - user-correction rows appended by `/correct`
- `data_collection_summary.json` - class balance + source composition + optional IAA score

## Recommended subfolders

- `raw/public_real_transactions.csv` - real/public anonymised records (target >= 500 rows)
- `raw/gold_double_labeled.csv` - optional double-labeled sample with `label_a,label_b` to compute inter-rater agreement

## Build curated train + gold split

```bash
python scripts/build_curated_datasets.py \
  --real data/raw/public_real_transactions.csv \
  --synthetic data/transactions_train.csv \
  --out-train data/transactions_train_curated.csv \
  --out-gold data/transactions_gold_eval.csv \
  --gold-size 300 \
  --dual-label data/raw/gold_double_labeled.csv
```

If `--dual-label` is provided, the script computes Cohen's kappa and writes it in `data_collection_summary.json`.
