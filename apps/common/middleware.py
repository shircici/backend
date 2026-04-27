import json
import time
import uuid
import logging

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
            try:
                count = cache.get(key, 0)
            except Exception:
                logger.warning("rate limit cache unavailable, fail-open path=%s", request.path)
                return self.get_response(request)
            limit = 120  # 120 writes / 60s / ip / path
            if count >= limit:
                return JsonResponse(
                    {"code": 429, "message": "too many requests", "data": None},
                    status=429,
                )
            try:
                if count == 0:
                    cache.set(key, 1, timeout=60)
                else:
                    cache.incr(key)
            except Exception:
                logger.warning("rate limit cache write unavailable, fail-open path=%s", request.path)
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
        try:
            cached = cache.get(data_key)
        except Exception:
            logger.warning("idempotency cache unavailable, bypass path=%s", request.path)
            return self.get_response(request)
        if cached:
            return JsonResponse(cached["body"], status=cached["status"])

        # Lock for concurrent duplicate requests.
        try:
            got_lock = cache.add(lock_key, str(time.time()), timeout=30)
        except Exception:
            logger.warning("idempotency lock cache unavailable, bypass path=%s", request.path)
            return self.get_response(request)
        if not got_lock:
            for _ in range(5):
                try:
                    cached = cache.get(data_key)
                except Exception:
                    cached = None
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
            try:
                cache.delete(lock_key)
            except Exception:
                pass
        return response


logger = logging.getLogger(__name__)


class GlobalSmsCircuitBreakerMiddleware:
    """
    全站短信请求量熔断中间件。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.endswith("/auth/sms/send-code") and request.method == "POST":
            limit = 10000
            key = f"sms:global:{time.strftime('%Y%m%d%H')}"
            try:
                count = cache.get(key, 0)
            except Exception:
                logger.warning("sms breaker cache unavailable, fail-open path=%s", request.path)
                return self.get_response(request)
            if count >= limit:
                logger.error("sms global limit reached key=%s count=%s", key, count)
                return JsonResponse({"code": 429, "message": "sms global rate limited", "data": None}, status=429)
            if int(count) == 0:
                try:
                    cache.set(key, 1, timeout=3700)
                except Exception:
                    logger.warning("sms breaker cache set unavailable, fail-open path=%s", request.path)
            else:
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, int(count) + 1, timeout=3700)
                except Exception:
                    logger.warning("sms breaker cache incr unavailable, fail-open path=%s", request.path)
        return self.get_response(request)


class SensitiveDataMaskingMiddleware:
    """
    对非管理员请求自动脱敏响应字段。
    """

    SENSITIVE_FIELDS = ("mobile", "phone", "id_card")

    def __init__(self, get_response):
        self.get_response = get_response

    def _mask(self, value):
        if not isinstance(value, str) or len(value) < 7:
            return value
        return f"{value[:3]}****{value[-4:]}"

    def _sanitize(self, payload):
        if isinstance(payload, list):
            return [self._sanitize(i) for i in payload]
        if isinstance(payload, dict):
            cleaned = {}
            for k, v in payload.items():
                lower = str(k).lower()
                if any(s in lower for s in self.SENSITIVE_FIELDS):
                    cleaned[k] = self._mask(v)
                else:
                    cleaned[k] = self._sanitize(v)
            return cleaned
        return payload

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        is_admin = bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))
        if is_admin:
            return response
        ctype = response.get("Content-Type", "")
        if "application/json" not in ctype:
            return response
        try:
            raw = json.loads(response.content.decode("utf-8"))
            masked = self._sanitize(raw)
            response.content = json.dumps(masked, ensure_ascii=False).encode("utf-8")
        except Exception:
            return response
        return response
