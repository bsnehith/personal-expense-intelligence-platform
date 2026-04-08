from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

genai_coach_invocations = Counter(
    "genai_coach_invocations_total",
    "Coach chat / monthly calls",
    ["endpoint"],
)
genai_coach_first_token_ms = Histogram(
    "genai_coach_first_token_ms",
    "Time to first streamed token",
    buckets=(10, 50, 100, 200, 500, 1000, 2000, 3000, 5000, 10000),
)


def metrics_response():
    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
