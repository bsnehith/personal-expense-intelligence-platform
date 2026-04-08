from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ml_service_endpoints_present():
    text = (ROOT / "ml-service" / "app.py").read_text(encoding="utf-8")
    for endpoint in ["/classify", "/classify_batch", "/correct", "/model-info", "/retrain"]:
        assert endpoint in text, f"Missing ml-service endpoint: {endpoint}"


def test_parser_and_gateway_endpoints_present():
    parser_text = (ROOT / "parser-service" / "app.py").read_text(encoding="utf-8")
    gateway_text = (ROOT / "api-gateway" / "main.py").read_text(encoding="utf-8")
    assert "/parse" in parser_text
    for endpoint in ["/upload", "/feed/stream", "/coach/stream", "/coach/monthly/stream", "/coach/statement"]:
        assert endpoint in gateway_text, f"Missing gateway endpoint: {endpoint}"


def test_frontend_pages_exist():
    pages = ROOT / "frontend" / "src" / "pages"
    for filename in [
        "LiveFeedPage.jsx",
        "UploadPage.jsx",
        "DashboardPage.jsx",
        "AnomaliesPage.jsx",
        "CoachPage.jsx",
        "ModelPage.jsx",
    ]:
        assert (pages / filename).exists(), f"Missing frontend page: {filename}"
