"""
短信验证码：生成、发送前限流、校验与消费（供视图与注册等复用）。
"""
from __future__ import annotations

import random
import secrets
import uuid
from datetime import date, datetime
from typing import Tuple

from django.conf import settings
from django.core.cache import cache
from django_redis import get_redis_connection

SMS_CODE_CACHE_PREFIX = "auth:sms:code:"
SMS_SEND_COOLDOWN_PREFIX = "auth:sms:send:cooldown:"
SMS_SEND_DAYCOUNT_PREFIX = "auth:sms:send:daycount:"
SMS_SEND_IP_COOLDOWN_PREFIX = "auth:sms:send:ip_cooldown:"
SMS_VERIFY_FAIL_PREFIX = "auth:sms:verify:fail:"
SMS_VERIFY_LOCK_PREFIX = "auth:sms:verify:locked:"
CAPTCHA_PREFIX = "auth:captcha:"
SMS_GLOBAL_HOURLY_PREFIX = "auth:sms:global:hour:"
DEVICE_PHONE_SET_PREFIX = "auth:device:phones:"
DEVICE_BLACKLIST_PREFIX = "auth:device:blacklist:"
SMS_VERIFY_SUCCESS_PREFIX = "auth:sms:verify:success:"


def _sms_code_ttl_seconds() -> int:
    return int(getattr(settings, "SMS_CODE_TTL_SECONDS", 300))


def _sms_send_min_interval_seconds() -> int:
    return int(getattr(settings, "SMS_SEND_MIN_INTERVAL_SECONDS", 60))


def _sms_send_daily_limit_phone() -> int:
    return int(getattr(settings, "SMS_SEND_DAILY_LIMIT_PHONE", 5))


def _sms_send_ip_min_interval_seconds() -> int:
    return int(getattr(settings, "SMS_SEND_IP_MIN_INTERVAL_SECONDS", 60))


def _sms_verify_max_failures() -> int:
    return int(getattr(settings, "SMS_VERIFY_MAX_FAILURES", 5))


def _sms_verify_lock_seconds() -> int:
    return int(getattr(settings, "SMS_VERIFY_LOCK_SECONDS", 900))


def generate_sms_code() -> str:
    length = random.randint(4, 6)
    return "".join(secrets.choice("0123456789") for _ in range(length))


def get_client_ip(meta: dict) -> str:
    xff = (meta.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return (meta.get("REMOTE_ADDR") or "").strip() or "unknown"


def create_captcha_challenge() -> dict:
    a = secrets.randbelow(10) + 1
    b = secrets.randbelow(10) + 1
    cid = str(uuid.uuid4())
    cache.set(f"{CAPTCHA_PREFIX}{cid}", str(a + b), timeout=120)
    return {"captcha_id": cid, "question": f"{a} + {b} = ?"}


def validate_captcha_if_required(captcha_id: str | None, captcha_answer: str | None) -> str | None:
    """若开启图形/人机校验，校验失败返回错误文案，否则返回 None。"""
    if not getattr(settings, "SMS_CAPTCHA_REQUIRED", False):
        return None
    if not captcha_id or captcha_answer is None or str(captcha_answer).strip() == "":
        return "请完成图形验证码"
    expected = cache.get(f"{CAPTCHA_PREFIX}{captcha_id}")
    cache.delete(f"{CAPTCHA_PREFIX}{captcha_id}")
    if expected is None:
        return "图形验证码已过期，请刷新"
    if str(captcha_answer).strip() != str(expected).strip():
        return "图形验证码错误"
    return None


def check_send_rate_limits(phone: str, client_ip: str) -> str | None:
    """
    发送前检查：手机号冷却、单日次数、同 IP 冷却。
    通过返回 None，否则返回错误信息（由视图映射为 429）。
    """
    cooldown_key = f"{SMS_SEND_COOLDOWN_PREFIX}{phone}"
    send_interval = _sms_send_min_interval_seconds()
    if send_interval > 0 and cache.get(cooldown_key):
        return "发送过于频繁，请稍后再试"

    day_key = f"{SMS_SEND_DAYCOUNT_PREFIX}{phone}:{date.today().isoformat()}"
    daily = int(cache.get(day_key) or 0)
    limit = _sms_send_daily_limit_phone()
    if limit > 0 and daily >= limit:
        return "该手机号今日发送次数已达上限"

    ip_key = f"{SMS_SEND_IP_COOLDOWN_PREFIX}{client_ip}"
    ip_interval = _sms_send_ip_min_interval_seconds()
    if ip_interval > 0 and cache.get(ip_key):
        return "请求过于频繁，请稍后再试"

    return None


def record_send_success(phone: str, client_ip: str) -> None:
    ttl = _sms_code_ttl_seconds()
    send_interval = _sms_send_min_interval_seconds()
    cooldown_key = f"{SMS_SEND_COOLDOWN_PREFIX}{phone}"
    if send_interval > 0:
        cache.set(cooldown_key, "1", timeout=send_interval)

    day_key = f"{SMS_SEND_DAYCOUNT_PREFIX}{phone}:{date.today().isoformat()}"
    n = int(cache.get(day_key) or 0)
    cache.set(day_key, n + 1, timeout=90000)

    ip_key = f"{SMS_SEND_IP_COOLDOWN_PREFIX}{client_ip}"
    ip_interval = _sms_send_ip_min_interval_seconds()
    if ip_interval > 0:
        cache.set(ip_key, "1", timeout=ip_interval)


def store_sms_code(phone: str, code: str) -> None:
    cache.set(f"{SMS_CODE_CACHE_PREFIX}{phone}", code, timeout=_sms_code_ttl_seconds())


def check_and_incr_global_sms_limit() -> str | None:
    """
    全局短信熔断：每小时最多允许发送 N 条，超限返回错误信息。
    """
    limit = int(getattr(settings, "SMS_GLOBAL_HOURLY_LIMIT", 10000))
    if limit <= 0:
        return None
    bucket = date.today().strftime("%Y%m%d")  # date portion fallback for key predictability
    hour = datetime.now().strftime("%H")
    key = f"{SMS_GLOBAL_HOURLY_PREFIX}{bucket}{hour}"
    current = cache.get(key)
    if current is None:
        cache.set(key, 1, timeout=3700)
        return None
    current_int = int(current)
    if current_int >= limit:
        return "短信通道繁忙，请稍后再试"
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, current_int + 1, timeout=3700)
    return None


def verify_sms_code_with_lua(phone: str, submitted_code: str) -> Tuple[bool, str | None, int]:
    """
    使用 Redis Lua 原子完成：比对成功即删除。
    """
    lock_key = f"{SMS_VERIFY_LOCK_PREFIX}{phone}"
    if cache.get(lock_key):
        return False, "验证尝试过多，请稍后再试", 429

    cache_key = f"{SMS_CODE_CACHE_PREFIX}{phone}"
    try:
        conn = get_redis_connection("default")
        script = """
        local value = redis.call('GET', KEYS[1])
        if not value then
            return 0
        end
        if tostring(value) == tostring(ARGV[1]) then
            redis.call('DEL', KEYS[1])
            return 2
        end
        return 1
        """
        rc = int(conn.eval(script, 1, cache_key, submitted_code.strip()))
    except Exception:
        return verify_sms_code_and_consume(phone, submitted_code)

    if rc == 2:
        cache.delete(f"{SMS_VERIFY_FAIL_PREFIX}{phone}")
        cache.delete(lock_key)
        cache.set(f"{SMS_VERIFY_SUCCESS_PREFIX}{phone}", "1", timeout=120)
        return True, None, 200
    if rc == 1:
        fail_key = f"{SMS_VERIFY_FAIL_PREFIX}{phone}"
        tries = int(cache.get(fail_key) or 0) + 1
        cache.set(fail_key, tries, timeout=_sms_code_ttl_seconds())
        if tries >= _sms_verify_max_failures():
            cache.set(lock_key, "1", timeout=_sms_verify_lock_seconds())
            cache.delete(cache_key)
            cache.delete(fail_key)
            return False, "验证尝试过多，请稍后再试", 429
        return False, "invalid or expired verification code", 400
    return False, "invalid or expired verification code", 400


def register_device_phone_attempt(device_id: str, phone: str) -> bool:
    """
    记录设备关联手机号，超过阈值拉黑，返回是否已拉黑。
    """
    if not device_id:
        return False
    limit = int(getattr(settings, "DEVICE_PHONE_DAILY_LIMIT", 5))
    set_key = f"{DEVICE_PHONE_SET_PREFIX}{device_id}"
    blacklist_key = f"{DEVICE_BLACKLIST_PREFIX}{device_id}"
    if cache.get(blacklist_key):
        return True
    try:
        conn = get_redis_connection("default")
        conn.sadd(set_key, phone)
        conn.expire(set_key, 24 * 3600)
        size = conn.scard(set_key)
        if int(size) > limit:
            conn.setex(blacklist_key, 24 * 3600, "1")
            return True
    except Exception:
        return False
    return False


def is_device_blacklisted(device_id: str) -> bool:
    if not device_id:
        return False
    return bool(cache.get(f"{DEVICE_BLACKLIST_PREFIX}{device_id}"))

def verify_sms_code_and_consume(phone: str, submitted_code: str) -> Tuple[bool, str | None, int]:
    """
    校验短信验证码；成功则删除验证码并清空失败计数。
    失败则累计失败次数，达到上限则锁定并删除验证码。
    返回 (成功, 错误信息, HTTP 状态码)。
    """
    lock_key = f"{SMS_VERIFY_LOCK_PREFIX}{phone}"
    if cache.get(lock_key):
        return False, "验证尝试过多，请稍后再试", 429

    submitted = submitted_code.strip()
    cache_key = f"{SMS_CODE_CACHE_PREFIX}{phone}"
    stored = cache.get(cache_key)
    stored_norm = str(stored).strip() if stored is not None else ""
    ok = bool(stored_norm) and submitted.casefold() == stored_norm.casefold()

    if ok:
        cache.delete(cache_key)
        cache.delete(f"{SMS_VERIFY_FAIL_PREFIX}{phone}")
        cache.delete(lock_key)
        return True, None, 200

    fail_key = f"{SMS_VERIFY_FAIL_PREFIX}{phone}"
    tries = int(cache.get(fail_key) or 0) + 1
    cache.set(fail_key, tries, timeout=_sms_code_ttl_seconds())

    if tries >= _sms_verify_max_failures():
        cache.set(lock_key, "1", timeout=_sms_verify_lock_seconds())
        cache.delete(cache_key)
        cache.delete(fail_key)
        return False, "验证尝试过多，请稍后再试", 429

    return False, "invalid or expired verification code", 400
