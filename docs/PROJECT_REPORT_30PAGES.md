# Personal Expense Intelligence Platform — 30-Page Submission Style Report

## 1) Abstract

This report describes the design and implementation of a Personal Expense Intelligence Platform that unifies real-time expense streaming, bank-statement document intelligence, machine learning-based categorization, anomaly detection, and generative AI coaching. The platform is implemented using a microservices architecture to separate responsibilities across ingestion (live simulation and statement parsing), categorization (ML inference and online learning), and advisory (GenAI coaching), while maintaining operational transparency through a dedicated observability stack.

Two ingestion pathways converge into a single categorization backbone. A live stream path publishes transactions through Kafka, enabling ML classification and event emission downstream. A statement upload path accepts user files (PDF/CSV/XLSX), extracts transaction rows using layered parsing and OCR techniques, normalizes them into a canonical schema, and then routes transactions through the same categorization logic to maintain consistency. Confidence-aware outputs include alternative category suggestions and review flags to support human-in-the-loop improvements.

User corrections are captured and fed back into training data, enabling correction-triggered retraining and model promotion governance. An anomaly engine identifies unusual spending behavior using a combination of statistical deviation checks and Isolation Forest behavior under cold-start conditions. System reliability and transparency are supported by Prometheus metrics, Grafana dashboards, and Loki log aggregation. Model lifecycle tracking is integrated through MLflow. This implementation demonstrates a complete, production-oriented engineering approach to applied personal financial intelligence.

## 2) Problem Background

Personal finance workflows involve heterogeneous transaction sources and unpredictable textual formats. Live card or UPI events arrive continuously, while monthly statements arrive as documents that may include tables, narrative lines, or scanned images. Correct categorization is difficult because merchant strings vary by formatting, spelling, language, and OCR noise. Moreover, static categorization models degrade over time as a user’s spending patterns and merchant conventions evolve.

In addition, many expense tools provide limited runtime transparency. When classification confidence is low, users typically do not receive actionable guidance or a clear justification for categorization. Without instrumentation, it is also difficult for developers to diagnose pipeline failures, such as OCR extraction errors, parsing mismatches, service startup ordering, or delayed downstream processing.

This project addresses these limitations by building a unified end-to-end platform that combines robust document intelligence, adaptive supervised categorization, continuous feedback-driven improvement, anomaly detection for unusual spend, and AI-based coaching. The architecture emphasizes reliable streaming and traceable observability to ensure the system is demonstrable and maintainable.

## 3) Objectives

The project objectives are:

1. Provide a unified pipeline that supports both live streaming transactions and statement-upload transactions.
2. Implement machine learning categorization with confidence scores and alternative labels for ambiguous cases.
3. Support correction-driven online learning, where user feedback influences future retraining.
4. Detect anomalies using hybrid methods adapted to user history maturity (cold start vs. mature users).
5. Provide GenAI coaching modules for interactive guidance and report summarization.
6. Achieve production-like reliability through containerized orchestration, SSE streaming, and service health checks.
7. Ensure system transparency using metrics, dashboards, and logs.

## 4) Scope and Assumptions

Scope includes:

1. Microservices implementing gateway orchestration, parsing, classification, coaching, and simulation.
2. Kafka-based event backbone for consistent streaming categorization.
3. OCR and document parsing components for PDF/CSV/XLSX statement ingestion.
4. Supervised learning models for category prediction and ensemble capabilities.
5. Correction mechanisms and retraining governance aligned with feedback thresholds.
6. Observability via Prometheus, Grafana, and Loki.
7. Project-level tests that validate endpoint and metrics contracts.

Assumptions:

1. User corrections are available through the product interface and are treated as high-value labels for training.
2. Statement documents may vary in format and quality; therefore layered extraction and fallback OCR are required.
3. The demonstration environment prioritizes local orchestration via Docker Compose, with optional extension for Grafana Cloud metrics export.
4. Security is primarily handled through environment variable configuration and secret hygiene practices; full enterprise access control is treated as future work.

## 5) Requirements (Functional and Non-Functional)

### Functional requirements

1. Provide a live transaction feed that displays categorised transactions in near real time.
2. Accept statement uploads in PDF/CSV/XLSX formats.
3. Extract transaction rows from documents using layered parsing and OCR fallback.
4. Normalize extracted transactions into a canonical schema that includes merchant text, amount, and dates.
5. Categorize transactions into a fixed taxonomy of expense categories and return confidence and alternatives.
6. Support user corrections for category labels and capture correction counts by category.
7. Trigger model retraining after correction thresholds or age-based conditions.
8. Implement anomaly detection to flag unusual spending behavior with structured reasons.
9. Provide GenAI coaching endpoints for interactive and summary-based guidance.
10. Expose metrics for pipeline quality, latency, and anomaly reporting to the monitoring stack.

### Non-functional requirements

1. Reliability: service health checks, dependency ordering, and fallback behavior for unavailable dependencies.
2. Performance: asynchronous service handling and SSE streaming for responsive UX.
3. Scalability: event-driven separation using Kafka topics for decoupled throughput scaling.
4. Maintainability: bounded services with clear responsibilities and contract-driven endpoints.
5. Observability: consistent metrics endpoint exposure and dashboard-ready instrumentation.
6. Reproducibility: seeded training data generation and consistent model artifact storage.
7. Compatibility: frontend integration through a gateway API base URL configuration.

## 6) Architecture Overview

The platform uses a microservices architecture with event-driven messaging for decoupling and scalability. The architecture is divided into ingestion, categorization, advisory, and observation components.

### Dual-path ingestion model

The system supports two ingestion pathways that converge into a common categorization pipeline:

1. Live stream path: simulator publishes transactions to Kafka topic `raw_transactions`; ML service consumes `raw_transactions`, enriches transactions via categorization and anomaly logic, and publishes to Kafka topic `categorised_transactions`; API gateway streams categorized events via SSE to the frontend.
2. Statement upload path: frontend uploads documents to API gateway; parser service extracts raw rows from PDF/CSV/XLSX and normalizes them; parser service routes normalized transactions through the Kafka and Redis upload queue (default unified pipeline) or falls back to synchronous classification modes; frontend receives SSE progress events for parsing and categorization completion.

### Core processing stages

The platform’s core stages are:

1. Parsing and normalisation (parser service)
2. Categorisation and confidence scoring (ML service)
3. Anomaly detection and anomaly reason generation (ML service)
4. Persistence and correction capture (PostgreSQL)
5. GenAI coaching and streaming narrative outputs (GenAI service)
6. Observability and monitoring (Prometheus, Grafana, Loki)

## 7) Component Diagram (Description for Placement)

Figure placeholders for a component diagram:

1. Figure A: System component blocks
   Frontend (React/Vite); API Gateway (FastAPI); Kafka (topics: `raw_transactions`, `categorised_transactions`); Redis (upload queue used for statement upload synchronization); Simulator (synthetic stream generator); Parser Service (PDF/CSV/XLSX parser, normaliser); ML Service (inference, Kafka consumer, correction logic, anomaly engine); PostgreSQL (transactions, corrections, parse event history); GenAI Service (coach streaming and report summarization); observability stack (Prometheus, Grafana, Loki, Promtail); and MLflow server (model tracking and optional registry).

2. Figure B: Data flow links
   Live pipeline link: simulator -> Kafka -> ML -> Kafka -> gateway SSE -> frontend. Upload pipeline link: frontend upload -> gateway -> parser -> Kafka+Redis -> ML -> Redis synchronization -> gateway SSE -> frontend.

The component diagram can be created in a diagram tool (Mermaid, draw.io, or Figma) and saved as `docs/architecture.png` if needed by your submission system.

## 8) Sequence Diagrams — Live Stream

Figure placeholders for the live stream sequence:

1. Figure C: Live Stream Sequence Diagram
   Steps: Simulator publishes a transaction to Kafka `raw_transactions`; the ML service consumes it, applies merchant cleaning, computes category prediction and confidence, and generates anomaly evaluation results; the ML service publishes enriched output to Kafka `categorised_transactions`; the API gateway streams the categorized events to the frontend via SSE; the frontend updates the live feed UI and displays confidence and anomaly indicators.

This diagram highlights the decoupling advantage of Kafka: ingestion and categorization progress independently while the gateway streams results without requiring direct synchronous classification calls.

## 9) Sequence Diagrams — Statement Upload

Figure placeholders for the statement upload sequence:

1. Figure D: Statement Upload Sequence Diagram
   Steps: the frontend selects a file and sends it to API gateway `POST /upload`; the API gateway proxies the request to parser-service `POST /parse` while streaming SSE chunks back to the browser; the parser service detects file type, extracts raw transaction rows, and normalizes them into canonical transaction schema fields; the parser service routes normalized transactions into the unified Kafka+Redis upload pipeline by publishing each row to Kafka `raw_transactions` with an `upload_session_id` and waiting for categorised results in a Redis queue; the ML service consumes `raw_transactions` and pushes categorized/enriched results to Redis when an `upload_session_id` is present; the parser service streams progress events back to the frontend (including `detect`, `extract`, and per-row `progress` updates); finally, the parser service returns a completion SSE event (`done`) and the frontend displays a completed categorized statement result.

This sequence emphasizes resilient document ingestion, progress transparency, and shared categorization logic with the live stream path.

## 10) Data Model and Schema Design

### A. Canonical transaction schema

The platform uses a canonical transaction schema to ensure all ingestion paths generate consistent inputs and outputs. Normalized transactions include:

1. `txn_id`: unique transaction identifier
2. `merchant_raw`: original merchant text extracted from source
3. `merchant_clean`: cleaned merchant text used by ML
4. `description`: merchant description representation
5. `amount`: normalized absolute transaction amount
6. `debit_credit`: debit or credit direction
7. `date`: normalized transaction date (YYYY-MM-DD)
8. `currency`: default INR (configurable in normalization)
9. `source`: statement_upload or api stream
10. `source_file`: original upload filename for traceability
11. `upload_session_id`: used to synchronize statement categorization results
12. Output enrichment fields include predicted `category`, prediction `confidence`, `alternatives` and `review_required` signals, and anomaly evaluation `anomaly` reasons/types.

### B. Kafka topics

The backbone uses two Kafka topics:

1. `raw_transactions`: emitted by simulator and parser after normalization
2. `categorised_transactions`: emitted by ML service after categorization and enrichment

### C. Redis queue usage

Redis is used to coordinate statement upload progress when Kafka ordering and UI streaming require session-aware synchronization. Each upload session is identified using a session id, and parser waits on a queue keyed by that session id.

### D. PostgreSQL schema

The database persistence layer is initialized with tables:

1. `transactions`
   stores `txn_id`, `user_id`, raw payload JSONB, `category`, `confidence`, `source`, and `source_file`
2. `corrections`
   stores correction events by `(txn_id, correct_category)`
3. `parse_events`
   stores upload parsing attempts including `filename`, detected `format`, success boolean, row count, and latency

This schema supports auditing corrections and improving training data, as well as tracking parser reliability over time.

## 11) API Design and Contracts

API design is implemented using a FastAPI API gateway for external access and internal microservice endpoints for orchestration.

### A. Gateway-facing API capabilities

Key gateway routes provide:

1. Health endpoint: `GET /health`
2. Metrics endpoint: `GET /metrics`
3. Live feed streaming: `GET /feed/stream` using SSE
4. Statement upload: `POST /upload` with streamed progress response
5. Correction and retraining:
   `POST /correct` and `POST /retrain`.
6. Model introspection:
   `GET /model-info`.
7. GenAI coaching endpoints:
   streaming chat `POST /coach/stream`, streaming monthly summary `POST /coach/monthly/stream`, and streaming statement summary `POST /coach/statement`.

### B. ML service contract

The ML service exposes:

1. `POST /classify`
2. `POST /classify_batch`
3. `POST /correct`
4. `POST /retrain`
5. `GET /model-info`

### C. Parser service contract

The parser service exposes:

1. `POST /parse` for parsing uploads and producing SSE progress output
2. `GET /metrics`
3. `GET /health`

### D. Contract verification via tests

Project tests validate endpoint presence and metric naming expectations to reduce regressions when components evolve. This improves submission robustness by ensuring that required contracts remain intact.

## 12) Parser Design

The parser service is responsible for statement document ingestion and conversion into raw transaction rows followed by normalization.

### A. Format detection

The parser uses:

1. File extension heuristics (PDF/CSV/XLSX)
2. Magic-byte detection for PDFs based on `%PDF` signature
3. Fallback classification if detection fails

### B. Parsing pipelines

1. PDF parsing pipeline: text extraction using pdfplumber; table extraction using pdfplumber page table extraction; alternate text extraction using PyMuPDF when needed; OCR fallback using PyMuPDF rasterization and Tesseract for scanned statements.
2. CSV parsing pipeline: robust CSV decoding with support for BOM stripping; flexible reading approach using pandas with separator fallback; column renaming heuristics into canonical `date`, `description`, `amount`, and debit/credit fields.
3. XLSX parsing pipeline: engine switching for legacy `.xls` and modern `.xlsx`; column normalization into canonical schema using substring-based matching.

### C. Progress streaming

The parser emits SSE progress events that allow the frontend to display steps such as detection, extraction, per-row categorization progress, and completion status.

## 13) OCR Pipeline

OCR is implemented as a layered and performance-aware pipeline designed for scanned statements.

### A. Image preprocessing

Before feeding images to OCR, preprocessing includes:

1. Deskew detection and correction using computer vision techniques
2. Contrast enhancement through CLAHE
3. Denoising via bilateral filtering
4. Upscaling for improved recognition of dense text
5. Adaptive thresholding to convert images into OCR-friendly binary forms

### B. Multi-pass OCR robustness

OCR uses multiple Tesseract page segmentation modes to improve detection across varied statement layouts. Each output is scored using heuristics that consider:

1. Transaction-related cue density (UPI, NEFT, IMPS, POS patterns)
2. Amount token presence

The highest-quality OCR result is selected as final OCR text for row extraction.

### C. Performance controls

To reduce latency cost, OCR scanning is applied to a capped subset of pages using a page selection method. The OCR process includes early stopping when enough parseable rows are detected.

## 14) Data Normalization

Normalization converts raw parser outputs into a canonical transaction dictionary suitable for ML inference and persistence.

Normalization includes:

1. Merchant text extraction and selection from multiple possible fields (description, narration, details, merchant, particulars)
2. Amount parsing: numeric extraction from strings; credit/debit inference based on sign and field selection; and normalized absolute amount output.
3. Debit/credit classification: uses source fields such as `type` or `dr_cr` when present; and falls back to debit by default.
4. Date normalization: converts multiple date formats into `YYYY-MM-DD` and uses UTC fallback when date is missing.
5. Merchant cleaning: reduces noise so ML focuses on stable tokens.
6. Canonical schema output fields including `source` and `source_file`

Canonicalization ensures consistent model input and predictable post-processing across all statement sources.

## 15) Category Taxonomy Rationale

The platform uses a 12-category expense taxonomy aligned with practical consumer finance classes:

1. `food_dining`
2. `transport`
3. `shopping`
4. `housing`
5. `health_medical`
6. `entertainment`
7. `travel`
8. `education`
9. `finance`
10. `subscriptions`
11. `family_personal`
12. `uncategorised`

The taxonomy design balances:

1. Coverage of common spending intents
2. Distinctiveness for machine learning classification
3. Practical handling of ambiguous or unseen transactions via `uncategorised`

This taxonomy is used consistently across training, inference, model evaluation, and UI display.

## 16) Baseline Model Approach (TF-IDF)

The baseline classifier uses TF-IDF features combined with a Logistic Regression model.

The baseline approach provides:

1. Fast inference suitable for real-time classification
2. Interpretability through lexical feature contributions (indirectly via model behavior)
3. Strong performance for merchant and description patterns that correlate with category labels

Model training uses:

1. A train/validation split
2. Weighted logistic regression to handle class imbalance
3. Confusion matrix reporting to identify systematic error patterns

This baseline is used as default configuration for efficiency.

## 17) Embedding Model Approach (MiniLM + Logistic Regression)

An embedding-based alternative uses sentence-transformer embeddings (MiniLM) to represent merchant and description text in a semantic vector space.

The embedding approach provides:

1. Better generalization when merchant strings differ lexically but share meaning
2. Increased robustness against spelling variations and format differences
3. Complementary decision behavior relative to TF-IDF lexical cues

The embedding model embeds text into vectors and trains Logistic Regression on top of those embeddings. Training and evaluation follow the same split policy as the baseline to support consistent comparisons.

## 18) Ensemble Approach (Stacked Model)

The platform supports a stacked ensemble that combines:

1. TF-IDF probability outputs
2. Embedding probability outputs
3. A meta-learner logistic regression that learns how to fuse these complementary signals

This approach improves accuracy by leveraging lexical cues and semantic similarity simultaneously. Because the ensemble requires additional computation (embedding generation and meta-learning), it is positioned as a higher-quality option when inference latency is acceptable.

## 19) Training and Evaluation Process

Training is conducted using data composed of:

1. Synthetic baseline data generation to bootstrap initial category coverage
2. Correction supplements collected from user corrections
3. Optional held-out gold evaluation dataset to support promotion gating and evaluation transparency

Core training pipeline steps:

1. Load and merge dataset sources.
2. Ensure the training dataset uses only valid taxonomy category labels.
3. Apply duplicate pruning (especially for combinations of merchant text, amount, and category).
4. Train selected model family (baseline, embedding, or ensemble).
5. Evaluate using accuracy and weighted F1-score.
6. Compute confusion matrix to support error analysis.
7. Write model artifacts and metadata, including evaluation statistics and promotion-related fields.
8. Optionally log experiments and metrics via MLflow.

The current deployed model artifacts include stored evaluation metrics and metadata to support reproducibility and report writing.

## 20) Online Learning and Corrections

Online learning is implemented through user correction intake, persistence, and retraining trigger logic.

Correction handling:

1. User submits corrected category for a transaction via a gateway correction endpoint.
2. ML service records correction counts and persists correction events to PostgreSQL.
3. The system stores transaction payload references when available to create training rows aligned with corrected labels.

Retraining triggers:

1. Correction-count threshold: retrain every N corrections (configurable).
2. Age-based threshold: retrain when a model reaches configured maximum age.

After retraining:

1. Model artifacts and metadata are updated.
2. ML service reloads the updated classifier to continue serving.

This design demonstrates a practical feedback loop essential for personalization in classification systems.

## 21) Anomaly Detection Methodology

Anomaly detection combines statistical deviation checks and model-based anomaly detection calibrated for user history maturity.

The approach includes:

1. Merchant novelty alerts after warm-up: detect first-time merchants for a given user after a minimum number of transactions.
2. Z-score deviation: compute per-user, per-category distribution of recent amounts and flag large deviations above a configurable Z-score threshold.
3. Isolation Forest evaluation for cold-start: for users with fewer transactions and insufficient history, Isolation Forest helps detect unusual spend shape against a wide synthetic baseline distribution.
4. Time-of-day checks: identify unusual spending patterns at specific hours for sensitive categories (for example, late-night food spend).

Anomaly outputs include structured reasons and types to support both UI display and future auditing.

## 22) GenAI Coaching Module

The GenAI coaching module provides interactive and summary-based guidance using streaming token generation.

The system supports:

1. Real-time chat coaching: users ask a question with current transaction context and the service streams token-by-token responses for responsive UI.
2. Monthly coaching summaries: summarization output streamed as tokens and intended for recurring insights on spending patterns.
3. Statement upload summary: a statement-specific advisory narrative derived from the transactions extracted and categorized from an uploaded file.

The API gateway proxies these streaming outputs, allowing the frontend to present a consistent user experience while keeping service topology abstracted.

## 23) Frontend Architecture and UX Flow

The frontend is built as a React single-page application with modular route-based pages. The UI modules include:

1. Live feed page: shows categorized transaction events in real time.
2. Upload page: handles statement upload and displays SSE-based progress events for parsing and categorization.
3. Dashboard page: shows analytical visualizations across categories and time patterns.
4. Anomalies page: displays flagged transactions and reasons.
5. Coach page: supports interactive GenAI chat and stream-based responses.
6. Model page: provides model status and retraining controls.

Interaction design emphasizes:

1. Streaming progress to reduce perceived latency during OCR-heavy parsing.
2. SSE consumption for real-time feed updates and streaming GenAI outputs.
3. Confidence and review signals to support human-in-the-loop correction workflows.

## 24) Deployment and DevOps Setup

Deployment is achieved through Docker Compose orchestration. The stack includes:

1. Kafka and Zookeeper for event backbone.
2. PostgreSQL for persistence.
3. Redis for upload session synchronization.
4. ML service and parser service built as separate containers.
5. GenAI service container.
6. API gateway container providing external endpoints.
7. Prometheus and Grafana for metrics visualization.
8. Loki and Promtail for log aggregation.
9. MLflow server container for experiment tracking and model metadata.

Operational reliability is enhanced via:

1. Health checks and dependency ordering with service-ready conditions.
2. Environment variables for consistent routing and behavior configuration.
3. Service fallback behavior when dependencies are unavailable.

An additional local-run approach is documented to support development environments where Docker engine behavior differs across machines.

## 25) Observability and Metrics Dashboarding

Observability is implemented via Prometheus instrumentation exposed through `/metrics` endpoints across all core services.

The platform’s observability coverage includes:

1. Categorization metrics include categorisation latency distribution, categorisation confidence tracking, and low-confidence rate metrics.
2. Pipeline metrics include Kafka consumer lag metrics and parser statement parse latency and success rate metrics.
3. Anomaly metrics include anomalies detected counters.
4. GenAI metrics include first-token or related token latency metrics.

Grafana dashboards are provisioned for categorization performance, pipeline health, and AI/anomaly views. Loki and Promtail provide searchable logs across containers.

Optional configuration supports Prometheus remote-write integration into Grafana Cloud for external monitoring continuity.

## 26) Testing Strategy and Quality Controls

Quality controls are implemented through a lightweight test suite that focuses on contracts and structural deliverables.

The tests validate:

1. Required service endpoints exist in each microservice.
2. Required metric names are present in metrics implementations.
3. Required frontend pages exist to meet demo deliverable constraints.
4. Required documentation deliverables exist in expected locations.

This approach minimizes fragile integration testing while ensuring the system still satisfies the critical interface and presentation requirements required for assessment.

## 27) Security and Secret Management

Security practices are based on:

1. Environment variable configuration for keys such as `GEMINI_API_KEY` used by the GenAI service.
2. Environment substitution for PostgreSQL connection strings and runtime routing.
3. Avoiding storing credentials directly inside code.

The repository contains configuration templates showing how secrets should be injected at runtime rather than hardcoded. Additionally, the project includes optional Prometheus remote-write configuration for Grafana Cloud metrics, where API tokens should be treated as secrets and rotated when exposure risk occurs.

Security limitations and future work include:

1. Implementing authentication and authorization for API endpoints.
2. Implementing secret scanning and enforced secret-free push policies in CI.
3. Adding stricter CORS and origin handling for production deployment.

## 28) Results and Current Performance Summary

Current model artifacts contain evaluation metrics and metadata that can be reported in this section:

1. Stored model version: TF-IDF baseline (`1.0.0-tfidf`)
2. Training rows: 3192
3. Stored evaluation accuracy: 1.0
4. Stored weighted F1-score: 1.0
5. Confusion matrix is diagonal in stored metadata, indicating no observed misclassification on the evaluation split used during artifact generation.

While these values demonstrate strong classifier separation under the specific evaluation conditions, the report should also mention that real-world performance depends on statement diversity, OCR noise rates, and merchant format drift. Correction feedback and anomaly flags are expected to improve long-term robustness.

Pipeline-level performance is monitored through:

1. Parser success rate and latency metrics.
2. ML categorization latency and confidence metrics.
3. Kafka consumer lag metrics.
4. Anomaly counters for event distribution awareness.

## 29) Limitations and Future Work

Limitations:

1. Perfect evaluation metrics depend on the dataset and evaluation split; real-world scanned document noise can reduce accuracy.
2. OCR extraction quality varies by statement layout, scan quality, and page selection coverage.
3. Anomaly detection is heuristic and depends on maintained user-specific history within the running service session.
4. CORS is configured broadly for development usability; production hardening is needed.
5. Correction-driven retraining depends on correction volume and timing, and may require careful promotion governance for safety in production.

Future work:

1. Add stronger drift detection and class-wise degradation monitoring over time.
2. Improve explainability outputs for both categorization and anomalies.
3. Expand integration tests to include end-to-end flows across Docker Compose in CI-like environments.
4. Add authentication/authorization for gateway endpoints and correction workflows.
5. Support richer annotation pipelines for gold evaluation set quality control and inter-rater tracking.
6. Improve OCR audit tooling to quantify extraction error types and optimize preprocessing parameters.
7. Implement CI/CD deployment pipelines with staged environment promotion and automated model registry promotion gates.

## 30) Final Conclusion and References

The Personal Expense Intelligence Platform demonstrates an end-to-end architecture that unifies real-time event streaming and document-driven transaction extraction with machine learning categorization and human-in-the-loop improvement. The platform’s microservices design supports bounded responsibilities across parsing, classification, anomaly evaluation, and AI coaching. Dual-path ingestion converges into a consistent categorization pipeline, enabling unified logic and shared monitoring.

The use of correction-driven retraining and configurable model families demonstrates a practical approach to personalization and model lifecycle governance. Observability via Prometheus, Grafana, and Loki provides the operational visibility required for reliability and debugging, while MLflow supports experiment tracking and reproducibility.

Overall, the project is a robust foundation for a scalable personal finance intelligence product. It provides both system-level engineering artifacts and algorithmic methods suitable for academic evaluation and portfolio demonstration.

References:

1. Martin Fowler, “Microservices: a definition of this new architectural term,” 2014. Available: https://martinfowler.com/articles/microservices.html
2. Apache Kafka documentation. Available: https://kafka.apache.org/documentation/
3. FastAPI documentation. Available: https://fastapi.tiangolo.com/
4. scikit-learn documentation. Available: https://scikit-learn.org/
5. sentence-transformers / MiniLM family documentation and research. (Sentence-BERT literature; see sentence-transformers project resources.)
6. Isolation Forest (ICDM 2008) original work and related scikit-learn references.
7. Prometheus documentation. Available: https://prometheus.io/docs/
8. Grafana documentation. Available: https://grafana.com/docs/
9. MLflow documentation. Available: https://mlflow.org/docs/latest/index.html
10. Loki and Promtail documentation (Grafana Loki ecosystem).

