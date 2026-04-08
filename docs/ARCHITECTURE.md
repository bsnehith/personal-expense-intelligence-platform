# Architecture Overview

The platform uses two input paths that converge into one categorisation pipeline:

1. **Path A (Live stream)**  
   `simulator -> Kafka(raw_transactions) -> ml-service -> Kafka(categorised_transactions) -> api-gateway SSE -> frontend`

2. **Path B (Statement upload)**  
   `frontend upload -> api-gateway -> parser-service -> Kafka(raw_transactions) -> ml-service -> Redis upload queue + Kafka(categorised_transactions) -> frontend`

Core stages:
- Parsing and normalisation (`parser-service`)
- Categorisation (`ml-service`)
- Anomaly detection (`ml-service/anomaly.py`)
- Storage and corrections (PostgreSQL + JSONL/csv supplements)
- GenAI coaching (`genai-service`)
- Observability (Prometheus + Grafana + Loki)

## Diagram asset
- Recommended demo asset path: `docs/architecture.png`
- You can export from draw.io/Figma/Mermaid and save using the path above.
