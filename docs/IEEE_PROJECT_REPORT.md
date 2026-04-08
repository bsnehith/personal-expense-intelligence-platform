# Personal Expense Intelligence Platform: A Microservices-Driven Approach for Real-Time Expense Categorization, Statement Intelligence, and Financial Coaching

## Abstract

This report presents the design and implementation of a Personal Expense Intelligence Platform that integrates real-time transaction streaming, statement document ingestion, machine learning-based categorization, anomaly detection, and generative AI-based financial coaching. The system is implemented as a modular microservices architecture using API gateway orchestration, event-driven messaging, and distributed observability. The platform supports dual ingestion paths: a continuous Kafka-backed simulator feed and user-uploaded bank statements parsed from PDF, CSV, and XLSX formats. Parsed and live transactions are normalized into a common schema and processed by a classification service with configurable model families, including TF-IDF logistic regression, sentence embedding-based classification, and a stacked ensemble. User corrections are captured and incorporated into retraining workflows to improve model relevance over time. An anomaly engine combines statistical and model-based checks for unusual spending behavior. Operational visibility is achieved via Prometheus, Grafana, and Loki, while ML lifecycle tracking is supported through MLflow. The work demonstrates a production-oriented implementation strategy for applied financial intelligence systems and establishes a foundation for scalable personal finance analytics.

## Keywords

Personal finance analytics, Expense categorization, Microservices, Kafka, OCR, Anomaly detection, MLflow, Prometheus, Grafana, Generative AI.

## I. Introduction

Digital personal finance usage has increased rapidly, yet many consumer tools still rely on simplistic transaction tagging, delayed reporting, and limited contextual guidance. Users typically manage heterogeneous data sources, such as live card activity and monthly statements, with inconsistent categories and minimal assistance for interpretation. These limitations reduce trust, increase manual correction effort, and hinder actionable decision-making.

The Personal Expense Intelligence Platform addresses these challenges by combining distributed data engineering with machine learning and AI-assisted interpretation. The central objective is to transform raw transactional signals into structured, explainable, and continuously improving financial insights. The platform is built to satisfy three practical requirements: (1) ingest expenses from both live and uploaded sources, (2) categorize and monitor spending reliably with correction loops, and (3) communicate insights through real-time dashboards and conversational coaching.

Unlike monolithic prototypes, this project adopts a service-separated architecture with explicit operational instrumentation. The result is an end-to-end system that supports experimentation, observability, and extensibility, suitable for academic evaluation and real-world MVP progression.

## II. Problem Definition and Objectives

### A. Problem Statement

Expense intelligence systems frequently underperform in environments where transaction text is noisy, merchant naming is inconsistent, and data arrives through mixed channels. Static models degrade over time when user behavior shifts, while statement extraction pipelines fail on low-quality scanned documents. In addition, many implementations do not expose sufficient runtime metrics to diagnose pipeline quality and latency bottlenecks.

### B. Objectives

The project objectives were defined as follows:

1. Build a dual-path ingestion platform for stream and statement inputs.
2. Provide unified transaction normalization and categorization for all input paths.
3. Implement correction-aware retraining workflows for adaptive performance.
4. Detect unusual transactions using user-aware anomaly techniques.
5. Deliver human-friendly explanations through AI coaching features.
6. Instrument all core services with production-style monitoring.
7. Support reproducible local deployment with containerized orchestration.

### C. Scope

The implementation scope includes backend services, frontend visualization modules, ML training and inference components, document parsing and OCR handling, observability stack setup, and project-level tests. Security hardening, enterprise identity/access management, and production cloud deployment automation are outside current scope and documented as future extensions.

## III. System Architecture

### A. Architectural Style

The platform follows a microservices architecture with event-driven communication for high-throughput and loose coupling. Services are organized by bounded responsibilities: gateway orchestration, parsing, classification, AI coaching, simulation, persistence, and monitoring. This decomposition improves maintainability and supports independent service evolution.

### B. Unified Dual-Path Data Flow

The architecture supports two input paths converging into a common categorization core:

1. **Live Stream Path**  
Simulator -> Kafka raw topic -> ML service -> Kafka categorized topic -> API gateway SSE -> Frontend.

2. **Statement Upload Path**  
Frontend upload -> API gateway -> Parser service -> Kafka raw topic -> ML service -> Redis upload queue + Kafka categorized topic -> Frontend progress stream.

This convergence model avoids duplicate logic and ensures consistency in category outputs, anomaly tagging, and downstream analytics regardless of source type.

### C. Service Responsibilities

- **API Gateway:** central entrypoint, CORS handling, SSE feed proxy, upload proxy, and service routing.
- **Parser Service:** file type detection, extraction, normalization, and upload progress eventing.
- **ML Service:** inference, Kafka consumer processing, correction intake, retraining control, and model metadata reporting.
- **GenAI Service:** conversational coaching and summary generation through streaming endpoints.
- **Simulator:** synthetic stream generation for integration and load scenarios.
- **PostgreSQL/Redis/Kafka:** persistence, queue coordination, and event backbone.
- **Observability stack:** metrics collection, dashboarding, and centralized logs.

## IV. Data Ingestion and Preprocessing

### A. Input Modalities

The system accepts:

- Continuous transaction events from simulator feed.
- User statement uploads in PDF, CSV, and XLSX formats.

### B. Parsing Strategy

For statement ingestion, parser logic combines format-sensitive extraction with robust fallback behavior. PDF handling uses layered extraction: text parsing, table extraction, alternate parser fallback, and OCR for scanned pages. CSV and XLSX parsers provide structured row extraction for tabular input sources.

### C. Transaction Normalization

Extracted rows are mapped into a canonical transaction schema containing merchant details, amount, date, direction, currency, source tags, and session context. Canonicalization ensures downstream compatibility across all ingestion channels and enables stable inference behavior.

### D. OCR Pipeline

Scanned statement support is achieved using image preprocessing and multi-pass OCR strategy. Preprocessing includes deskewing, contrast enhancement, denoising, adaptive thresholding, and scaling to improve recognition quality. Multi-pass OCR configuration and quality heuristics reduce extraction failure rates for degraded statement scans.

## V. Machine Learning Design

### A. Classification Task

The core ML task is multiclass expense categorization across a fixed taxonomy of personal spending categories. The system predicts category labels, confidence scores, and alternative label candidates for ambiguous transactions.

### B. Model Families

Three model families are supported:

1. **TF-IDF + Logistic Regression (baseline):** efficient lexical classifier for fast inference.
2. **Sentence Embedding + Logistic Regression:** semantic representation using transformer embeddings for improved contextual capture.
3. **Stacked Ensemble:** meta-learning layer combining probability outputs from lexical and semantic base learners.

This configurable approach enables performance-versus-latency tradeoff selection based on deployment needs.

### C. Feature Construction

Input representation combines merchant text, description text, and amount-token signals. This hybrid encoding captures lexical signatures and value-aware transaction context while remaining practical for lightweight model training.

### D. Data Sources and Labeling

Training data is assembled from synthetic baseline generation and user correction supplements. Optional held-out gold evaluation data is used for promotion gating but excluded from fitting. This arrangement balances bootstrapping speed with controlled quality checks.

### E. Evaluation Metrics

Model performance tracking includes:

- Accuracy
- Weighted F1-score
- Confusion matrix
- Optional gold-set metrics when available

These metrics are stored in model metadata and logged to tracking infrastructure when configured.

## VI. Online Learning and Model Lifecycle

### A. Correction Loop

The platform captures user-provided category corrections and records correction counts by class. Correction records are appended to supplemental training data, creating a practical user-in-the-loop learning mechanism.

### B. Retraining Triggers

Retraining can occur manually or automatically based on configurable thresholds, including correction count triggers and model-age criteria. After retraining, model artifacts and metadata are reloaded into inference service context.

### C. Promotion Policy

A threshold-based promotion policy is implemented using configurable minimum accuracy criteria, with preference for held-out gold metrics when present. This policy provides controlled progression from training outputs to active serving artifacts.

### D. Experiment Tracking

MLflow integration supports logging of parameters, metrics, and artifacts. Optional registry transitions provide a foundation for more formalized model release workflows.

## VII. Anomaly Detection Methodology

Anomaly detection is designed as a hybrid strategy aligned with user history maturity:

- **Z-score based deviation:** applied when sufficient category-specific historical samples exist.
- **Isolation Forest evaluation:** applied for cold-start conditions with sparse user history.
- **First-time merchant alerting:** triggered after warm-up to reduce early-stage noise.
- **Time-pattern checks:** highlights unusual hour-based spending behavior for selected categories.

This design balances statistical reliability and practical early-user utility.

## VIII. API and Communication Design

### A. Integration Pattern

Frontend clients communicate only with the gateway layer, which proxies requests to internal services. This shields clients from service topology and supports cleaner future security controls.

### B. Streaming Interfaces

Server-Sent Events are used for:

- Live categorized feed updates.
- Upload progress notifications during parsing and categorization.
- Token-wise GenAI response streaming.

SSE was selected for simplicity, browser compatibility, and low infrastructure overhead relative to full-duplex protocols.

### C. Reliability Considerations

Gateway-level fallback responses and service availability hints are implemented to improve fault transparency when dependent services are unreachable or still initializing.

## IX. Frontend Experience and Analytical Modules

The user interface is structured into route-separated modules for feed monitoring, upload workflows, dashboard analytics, anomaly review, coaching interaction, and model status introspection. This modular UI organization supports task-oriented navigation and clear separation between operational monitoring and user-level insights.

Progressive upload feedback, live feed visualization, and coaching streams improve perceived responsiveness and user trust in long-running backend operations such as OCR and batch categorization.

## X. Observability and Operational Analytics

### A. Metrics Layer

Prometheus endpoints are exposed by gateway, parser, ML, and GenAI services. Instrumentation includes latency, confidence distribution, correction counters, parse success ratio, anomaly counts, and SSE-related gauges.

### B. Visualization Layer

Grafana dashboards are provisioned for:

- Categorization performance monitoring
- Pipeline health and throughput behavior
- Anomaly and AI-coach-related operational views

### C. Log Aggregation

Loki and Promtail enable centralized log shipping and indexed exploration for troubleshooting cross-service issues.

### D. Cloud Metrics Export

A dedicated Prometheus configuration supports optional remote-write integration for Grafana Cloud, enabling external observability continuity beyond local setup.

## XI. Deployment and Environment Management

Container orchestration is implemented via Docker Compose with explicit service dependencies, health checks, mounted volumes, and environment-based configuration. Supporting infrastructure includes Kafka, Zookeeper, PostgreSQL, Redis, MLflow server, and observability services.

The project also documents local fallback execution paths for scenarios where full container orchestration is temporarily unavailable.

## XII. Testing and Verification Approach

Project-level tests validate endpoint contracts, metric naming expectations, and repository deliverable structure. The test strategy emphasizes fast execution and lightweight smoke coverage suitable for continuous local validation without requiring full-stack startup in every run.

This approach provides rapid regression signals while preserving development velocity.

## XIII. Results and Progress Assessment

### A. Implementation Maturity

Current progress demonstrates full-stack integration maturity across ingestion, parsing, ML inference, feedback-driven retraining, anomaly analysis, coaching, and observability. The implemented architecture is coherent and demonstrably operational as an end-to-end platform.

### B. Technical Outcomes

Major outcomes achieved include:

- Unified categorization pipeline for both live and document-derived transactions.
- Configurable ML strategy supporting baseline and advanced model families.
- User-correction pipeline that enables adaptive model behavior.
- Document intelligence pipeline resilient to scanned and noisy statements.
- Production-style monitoring and log observability across services.

### C. Engineering Strengths

The platform exhibits strong separation of concerns, event-driven scalability principles, and practical MLOps design elements uncommon in early-stage academic prototypes.

## XIV. Limitations and Future Work

Despite strong implementation progress, several enhancements can further strengthen the platform:

1. Expanded integration and performance benchmarking under higher real-world load.
2. Drift monitoring and class-wise degradation alerts for long-term model governance.
3. Enhanced explainability features for model predictions and anomaly decisions.
4. Improved security posture with stricter secret management and access control layers.
5. Richer annotation workflow for gold dataset curation and inter-rater consistency tracking.
6. Cloud-native deployment pipeline with CI/CD automation and environment promotion gates.

These extensions are natural next steps and do not diminish current system completeness for MVP and demonstration contexts.

## XV. Conclusion

This work presents a comprehensive and practically engineered Personal Expense Intelligence Platform that unifies stream processing, document parsing, machine learning categorization, anomaly detection, and AI-assisted financial communication in a microservices architecture. The project moves beyond isolated model experimentation by integrating operational observability, retraining workflows, and user-feedback loops into a coherent product system.

The current implementation establishes a strong foundation for both academic reporting and real-world evolution. It demonstrates that robust personal finance intelligence can be built with modular service boundaries, adaptive ML strategies, and transparent operational tooling.

## References

[1] M. Fowler, "Microservices: a definition of this new architectural term," 2014. [Online]. Available: https://martinfowler.com/articles/microservices.html  
[2] Apache Software Foundation, "Apache Kafka Documentation." [Online]. Available: https://kafka.apache.org/documentation/  
[3] FastAPI, "FastAPI Documentation." [Online]. Available: https://fastapi.tiangolo.com/  
[4] Scikit-learn Developers, "Scikit-learn: Machine Learning in Python." [Online]. Available: https://scikit-learn.org/  
[5] N. Reimers and I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," in *Proc. EMNLP-IJCNLP*, 2019.  
[6] F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation Forest," in *Proc. ICDM*, 2008.  
[7] Tesseract OCR, "Tesseract User Manual." [Online]. Available: https://tesseract-ocr.github.io/  
[8] Prometheus Authors, "Prometheus Documentation." [Online]. Available: https://prometheus.io/docs/  
[9] Grafana Labs, "Grafana Documentation." [Online]. Available: https://grafana.com/docs/  
[10] MLflow, "MLflow Documentation." [Online]. Available: https://mlflow.org/docs/latest/index.html
