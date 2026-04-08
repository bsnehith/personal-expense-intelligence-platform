from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

upload_bytes_total = Counter("gateway_upload_bytes_total", "Bytes proxied via /upload")
active_sse_feeds = Gauge("gateway_sse_feeds_active", "Active feed streams (approx)")


def metrics_response():
    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
