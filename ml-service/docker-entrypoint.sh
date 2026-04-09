#!/bin/sh
set -e
EMB_FLAG=""
ENS_FLAG=""
ALL_FLAG=""
if [ "$USE_EMBEDDING_MODEL" = "1" ]; then EMB_FLAG="--embedding"; fi
if [ "$USE_ENSEMBLE" = "1" ]; then ENS_FLAG="--ensemble"; fi
if [ "$USE_ALL_MODELS" = "1" ]; then ALL_FLAG="--all-models"; EMB_FLAG=""; ENS_FLAG=""; fi
if [ "$TRAIN_ON_BOOT" = "1" ] && [ ! -f "$MODEL_DIR/metadata.json" ]; then
  echo "[ml-service] Training initial model..."
  if [ -f "$DATA_DIR/transactions_train.csv" ]; then
    python -m model.train --out "$MODEL_DIR" --data "$DATA_DIR/transactions_train.csv" $ALL_FLAG $ENS_FLAG $EMB_FLAG
  else
    python -m model.train --out "$MODEL_DIR" $ALL_FLAG $ENS_FLAG $EMB_FLAG
  fi
fi
exec uvicorn app:app --host 0.0.0.0 --port 8001
