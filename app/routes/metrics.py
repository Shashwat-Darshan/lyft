"""Prometheus metrics endpoint."""
from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "status"]
)

webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total webhook processing outcomes",
    ["result"]
)

request_latency_ms = Histogram(
    "request_latency_ms",
    "Request latency in milliseconds",
    buckets=[100, 500, 1000, 2000, 5000, float("inf")]
)


@router.get("/metrics")
async def metrics():
    """Expose Prometheus-style metrics in text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

