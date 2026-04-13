import json
import time
import uuid

from django.core.cache import cache
from django.http import JsonResponse

from .metrics import API_REQUEST_LATENCY, API_REQUEST_TOTAL


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed = time.perf_counter() - started
        path = request.path
        method = request.method
        status_code = str(getattr(response, "status_code", 500))
        API_REQUEST_TOTAL.labels(method=method, path=path, status_code=status_code).inc()
        API_REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        return response


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class SimpleRateLimitMiddleware:
    """
    Lightweight per-IP per-path limiter.
    Tuned for write APIs to protect downstream DB/queue.
    """

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in self.WRITE_METHODS:
            ip = request.META.get("REMOTE_ADDR", "unknown")
            key = f"ratelimit:{ip}:{request.path}"
            count = cache.get(key, 0)
            limit = 120  # 120 writes / 60s / ip / path
            if count >= limit:
                return JsonResponse(
                    {"code": 429, "message": "too many requests", "data": None},
                    status=429,
                )
            if count == 0:
                cache.set(key, 1, timeout=60)
            else:
                cache.incr(key)
        return self.get_response(request)


class IdempotencyMiddleware:
    """
    Accept X-Idempotency-Key for write requests.
    If same key is replayed within TTL, return saved response.
    """

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in self.WRITE_METHODS:
            return self.get_response(request)

        idem_key = request.headers.get("X-Idempotency-Key", "").strip()
        if not idem_key:
            return self.get_response(request)

        base_key = f"idempotency:{request.path}:{idem_key}"
        lock_key = f"{base_key}:lock"
        data_key = f"{base_key}:response"
        cached = cache.get(data_key)
        if cached:
            return JsonResponse(cached["body"], status=cached["status"])

        # Lock for concurrent duplicate requests.
        got_lock = cache.add(lock_key, str(time.time()), timeout=30)
        if not got_lock:
            for _ in range(5):
                cached = cache.get(data_key)
                if cached:
                    return JsonResponse(cached["body"], status=cached["status"])
                time.sleep(0.05)

        response = self.get_response(request)
        try:
            body = json.loads(response.content.decode("utf-8"))
            cache.set(data_key, {"status": response.status_code, "body": body}, timeout=600)
        except Exception:
            pass
        finally:
            cache.delete(lock_key)
        return response
