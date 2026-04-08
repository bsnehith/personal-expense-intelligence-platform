from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_required_metrics_defined():
    ml_metrics = _read(ROOT / "ml-service" / "metrics.py")
    parser_app = _read(ROOT / "parser-service" / "app.py")
    genai_metrics = _read(ROOT / "genai-service" / "metrics.py")

    required = [
        "categorisation_latency_ms",
        "categorisation_confidence",
        "low_confidence_rate",
        "user_corrections_total",
        "model_accuracy_current",
        "anomalies_detected_total",
        "kafka_consumer_lag",
        "statement_parse_latency_ms",
        "statement_parse_success_rate",
        "genai_coach_first_token_ms",
    ]

    blob = "\n".join([ml_metrics, parser_app, genai_metrics])
    for metric in required:
        assert metric in blob, f"Metric missing from implementation: {metric}"
