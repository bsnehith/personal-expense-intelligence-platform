from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_paths_exist():
    required = [
        ROOT / "simulator" / "generator.py",
        ROOT / "parser-service" / "app.py",
        ROOT / "ml-service" / "app.py",
        ROOT / "genai-service" / "app.py",
        ROOT / "api-gateway" / "main.py",
        ROOT / "frontend" / "src" / "App.jsx",
        ROOT / "observability" / "prometheus.yml",
        ROOT / "observability" / "grafana" / "dashboards",
        ROOT / "docker-compose.yml",
        ROOT / ".env.example",
        ROOT / "README.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    assert not missing, f"Missing required paths: {missing}"


def test_deliverable_docs_exist():
    required_docs = [
        ROOT / "docs" / "MODEL_CARD.md",
        ROOT / "docs" / "DATA_COLLECTION_REPORT.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "tests" / "README.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required_docs if not p.exists()]
    assert not missing, f"Missing deliverable docs: {missing}"
