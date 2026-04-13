from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from django.http import HttpResponse

API_REQUEST_TOTAL = Counter(
    "api_request_total",
    "Total API requests",
    ["method", "path", "status_code"],
)

API_REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "API latency in seconds",
    ["method", "path"],
)


def metrics_view(_request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
