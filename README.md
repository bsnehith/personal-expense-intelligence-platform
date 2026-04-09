# Personal Expense Intelligence Platform

End-to-end stack aligned with the project brief: **Kafka** live feed, **ML** categorisation (TF‑IDF / embeddings / **stacked ensemble**), **PostgreSQL** + **Redis**, **statement parsing** (pdfplumber, **PyMuPDF**, **Tesseract + OpenCV** OCR), **Gemini** coach, **MLflow**, **Prometheus**, **Grafana**, **Loki**.

## Quick start

**Backend (Docker):**

```bash
docker compose up --build
```

**Frontend** (separate terminal, from repo root):

```bash
cd frontend
npm install
npm run dev
```

Optional: `node scripts/ensure-frontend-env.mjs` creates `frontend/.env` with `VITE_API_BASE_URL=http://localhost:8000`.

### Docker Desktop errors (`500`, `dockerDesktopLinuxEngine`)

That comes from the **Docker engine on Windows**, not this repo. Restart Docker Desktop; if `docker ps` still fails, see **[docs/LOCAL_DEV.md](docs/LOCAL_DEV.md)** to run **Postgres/Kafka/Redis** via `docker compose -f docker-compose.infra.yml` and the **Python services on the host**, or use `scripts/run-backend-local.ps1 -Launch` after infra is up.

### Run backend without full Compose (local Python)

1. `.\scripts\setup-local-deps.ps1` (Python 3.12; installs each service’s `requirements.txt`)  
2. `docker compose -f docker-compose.infra.yml up -d` (when Docker can run images)  
3. Follow **[docs/LOCAL_DEV.md](docs/LOCAL_DEV.md)** or `powershell -ExecutionPolicy Bypass -File scripts/run-backend-local.ps1 -Launch`

- **Frontend:** http://localhost:5173 — ensure `frontend/.env` has `VITE_API_BASE_URL=http://localhost:8000`
- **API gateway:** http://localhost:8000  
- **Grafana:** http://localhost:3001 (admin / admin)  
- **Prometheus:** http://localhost:9090  
- **MLflow UI:** http://localhost:5000  
- **Loki:** http://localhost:3100 (wire in Grafana as datasource)

## Services (Docker Compose)

| Service | Port | Role |
|---------|------|------|
| api-gateway | 8000 | CORS, SSE `/feed/stream`, `/upload` (20MB max), proxies |
| ml-service | 8001 | `/classify`, `/correct`, `/retrain`, `/model-info`, `/metrics`, Kafka consumer |
| parser-service | 8002 | PDF / CSV / XLSX, Kafka `raw_transactions` + Redis upload queue |
| genai-service | 8003 | Gemini coach, `/metrics` |
| postgres | 5432 | transactions, corrections, parse_events; MLflow backend store |
| redis | 6379 | upload session queue (Kafka path) |
| kafka | 9092 / 29092 | `raw_transactions`, `categorised_transactions` |
| prometheus | 9090 | scrapes all `/metrics` endpoints |
| grafana | 3001 | Prometheus + Loki datasources |
| promtail | 9080 | ships Docker logs to Loki |
| mlflow | 5000 | experiment tracking (uses Postgres) |

## Data & training

```bash
python scripts/generate_training_data.py   # → data/transactions_train.csv
```

- **Best-accuracy mode (recommended):** set `USE_ALL_MODELS=1` or pass `--all-models` to train TF‑IDF, embedding, and ensemble families, then persist the top model by weighted F1.  
- **Default boot model:** fast TF‑IDF (`USE_ENSEMBLE=0`, `USE_ALL_MODELS=0`).  
- **Ensemble only (TF‑IDF + MiniLM + meta‑LR):** set `USE_ENSEMBLE=1` (slow first train; downloads MiniLM).  
- **Retraining:** `POST /retrain` or automatic every **50** corrections (`RETRAIN_CORRECTION_THRESHOLD`).  
- **MLflow:** training logs to `MLFLOW_TRACKING_URI` when set (Docker: `http://mlflow:5000`).
- **Curated real+synthetic split helper:** `python scripts/build_curated_datasets.py ...` (outputs train + held-out gold + summary JSON including optional inter-rater kappa).

## Environment (`.env`)

See `.env.example`. Important keys:

- `GEMINI_API_KEY`, `GEMINI_MODEL`  
- `USE_ALL_MODELS`, `USE_ENSEMBLE`, `USE_EMBEDDING_MODEL`  
- `MONTHLY_AUTO_REVIEW_ENABLED`, `MONTHLY_AUTO_REVIEW_USER_ID`  
- `RETRAIN_CORRECTION_THRESHOLD`  
- `TX_INTERVAL_SEC` (simulator; use `0.1` for ~10 tx/sec load tests)  
- User corrections append labelled rows to `data/correction_supplement.csv` (merged on retrain) when `POST /correct` includes transaction fields or Postgres has the txn payload.  
- `USE_KAFKA_UPLOAD_PATH=0` — parser falls back to direct `/classify` (no Redis/Kafka ordering) if needed  

**Postgres / MLflow auth errors (`role "expense" does not exist`, password failed):** the DB is only initialized on first use of an empty data volume. From the repo root run `docker compose down -v` (removes Compose volumes, including Postgres data), then `docker compose up --build`. The stack uses the named volume `expense_platform_pgdata` for Postgres; leftover old `pgdata` volumes from earlier Compose versions can be deleted in Docker Desktop if they are unused.

## Unified upload pipeline

When **Kafka + Redis** are available (default in Compose): each statement row is published to **`raw_transactions`** (same topic as the simulator), the **ml-service** consumer classifies, publishes **`categorised_transactions`**, and **pushes** the enriched row to **Redis** so the parser SSE can stream progress. If Redis/Kafka are unavailable, the parser uses synchronous `/classify`.

## Observability

Prometheus scrapes: `api-gateway:8000`, `ml-service:8001`, `parser-service:8002`, `genai-service:8003`.  
Grafana (http://localhost:3001) auto-loads three starter dashboards from `observability/grafana/dashboards/` (categorisation performance, pipeline health, anomaly + GenAI).  
Loki is provisioned as a datasource; `promtail` in `docker-compose.yml` ships container logs for search in Grafana Explore.
Alert rules are defined in `observability/alerts.yml` (latency, confidence, parse success, model accuracy, consumer lag).

## Tests

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest tests -q
```

Project-level tests live in `tests/` and validate required contracts (endpoints, metrics, and structure).

## Deliverable docs

- Model Card: `docs/MODEL_CARD.md`
- Data Collection Report: `docs/DATA_COLLECTION_REPORT.md`
- Architecture note: `docs/ARCHITECTURE.md`
- Notebook workspace: `notebooks/README.md` and `notebooks/model_training_evaluation.ipynb`

If your assessor requires a PNG specifically at `docs/architecture.png`, run:

```bash
python scripts/prepare_demo_assets.py
```

## API contract (frontend)

Matches `frontend/src/lib/api.js`: `/feed/stream`, `/upload`, `/correct`, `/anomaly-action`, `/retrain`, `/model-info`, `/coach/stream`, `/coach/monthly`, `/coach/statement`, `/coach/monthly/latest` (backend auto monthly cache).
