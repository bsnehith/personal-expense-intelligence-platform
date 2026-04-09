# Data Collection Report

## Objective
Build a reproducible, balanced transaction dataset for 12-category expense classification without keyword-rule labeling.

## Data Sources
1. **Synthetic baseline generation**
   - Generated using project simulator/templates and `scripts/generate_training_data.py`.
   - Provides broad category coverage and realistic transaction string formats.
2. **Runtime simulator stream**
   - Kafka producer (`simulator/generator.py`) emits additional realistic samples for stress/integration scenarios.
3. **User correction supplements**
   - Captured through `POST /correct`.
   - Persisted to `data/correction_supplement.csv` and merged during retraining.
4. **Gold evaluation set (recommended)**
   - `data/transactions_gold_eval.csv` (manually labeled).
   - Used for evaluation only, never for training.

## Labeling Strategy
- Category IDs match `ml-service/model/categories.py`.
- Synthetic labels are programmatically generated from category templates.
- Human corrections are treated as high-value labels for hard/ambiguous cases.
- Gold set should be manually reviewed for consistency before use.

## Split Policy
- Curated split helper: `scripts/build_curated_datasets.py`
  - Combines real/public + synthetic rows
  - Produces `data/transactions_train_curated.csv`
  - Produces held-out `data/transactions_gold_eval.csv` (default 300 rows)
- Training pipeline performs internal train/validation split.
- Gold evaluation set is held-out and excluded from fit data.
- Promotion gate prefers gold-set metrics when available.

## Quality Controls
- Enforce category IDs from taxonomy only.
- Remove duplicate combinations (`merchant_raw`, `amount`, `category`) during training load.
- Track corrections by category to spot weak classes.
- Maintain minimum examples per class (recommended >= 100).
- Optional inter-rater agreement:
  - Provide `--dual-label data/raw/gold_double_labeled.csv` with `label_a,label_b`
  - Script computes Cohen's kappa and writes it to `data/data_collection_summary.json`

## Current Gaps to Track
- Add periodic audit of OCR-derived labels from scanned statements.

## Reproducibility
- Synthetic generation script is deterministic with seeded randomness.
- Training metadata is written to `ml-service/model/artifacts/metadata.json`.
- MLflow logging records params/metrics/artifacts when configured.
