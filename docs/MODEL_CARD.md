# Model Card - Expense Categoriser

## Model Details
- **Task**: Multi-class transaction categorisation into 12 labels.
- **Service**: `ml-service`
- **Primary entrypoints**: `POST /classify`, `POST /classify_batch`, `POST /correct`, `GET /model-info`
- **Current families supported**:
  - TF-IDF + Logistic Regression (default)
  - MiniLM embeddings + Logistic Regression
  - Stacked ensemble (TF-IDF + MiniLM + meta-learner)

## Taxonomy
- `food_dining`
- `transport`
- `shopping`
- `housing`
- `health_medical`
- `entertainment`
- `travel`
- `education`
- `finance`
- `subscriptions`
- `family_personal`
- `uncategorised`

## Training Data
- **Target size**: >= 3,000 labelled rows.
- **Current pipeline**:
  - Synthetic records from simulator/template generation.
  - Supplement records from user corrections (`data/correction_supplement.csv`).
  - Optional gold eval set (`data/transactions_gold_eval.csv`) used only for evaluation gate.
- **Expected split**:
  - Train/validation split in `ml-service/model/train.py`.
  - Gold eval set is held out and never used for fitting.

## Features
- Text: `merchant_raw + description + amount token`.
- Numeric signal: amount embedded into text token (`amt=<value>`) in baseline.
- Optional semantic embeddings via sentence-transformers (`all-MiniLM-L6-v2`).

## Metrics Reported
- `eval_accuracy`
- `eval_f1_weighted`
- confusion matrix
- per-category classification report (precision/recall/f1/support)
- optional gold-set metrics:
  - `gold_eval_accuracy`
  - `gold_eval_f1_weighted`

## Promotion Policy
- Promotion threshold controlled by `MODEL_PROMOTION_MIN_ACC` (default `0.80`).
- Gate metric:
  - `gold_eval_accuracy` if gold set exists.
  - otherwise fallback to `eval_accuracy`.
- MLflow registry promotion can be automated when enabled.
- In `USE_ALL_MODELS=1`, trainer benchmarks TF-IDF, embedding, and ensemble families and promotes the best model by weighted F1.

## Online Learning
- Corrections are written via `POST /correct`.
- Correction rows are appended to `data/correction_supplement.csv`.
- Retrain triggers:
  - every `RETRAIN_CORRECTION_THRESHOLD` corrections (default 50), or
  - age-based threshold (`RETRAIN_MAX_AGE_HOURS`).

## Known Failure Modes
- Ambiguous merchants across categories (shopping vs subscriptions).
- OCR noise from scanned PDFs can degrade category confidence.
- Cold-start users have noisier anomaly context and weaker personalised signals.
- Unseen regional/local merchant formats may lower confidence.

## Responsible Use Notes
- This model provides guidance, not financial/legal advice.
- Keep credentials out of repo and rotate keys on exposure.
- Avoid storing raw sensitive PII in training artifacts.
