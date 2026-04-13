import json
import time

from django.core.cache import cache


def _cache_key(sku_code: str) -> str:
    return f"sku:detail:{sku_code}"


def get_cached_sku(sku_code: str):
    val = cache.get(_cache_key(sku_code))
    if not val:
        return None
    return json.loads(val)


def set_cached_sku(sku_code: str, payload: dict, ttl: int = 300):
    cache.set(_cache_key(sku_code), json.dumps(payload), timeout=ttl)


def invalidate_sku_cache(sku_code: str):
    cache.delete(_cache_key(sku_code))


def with_cache_breakdown_protection(sku_code: str, loader, ttl: int = 300):
    """
    Cache breakdown protection:
    - Try cache first
    - If miss, acquire short lock with cache.add()
    - The winner loads DB and sets cache
    - Others spin briefly then read cache
    """
    cached = get_cached_sku(sku_code)
    if cached is not None:
        return cached

    lock_key = f"sku:detail:lock:{sku_code}"
    has_lock = cache.add(lock_key, "1", timeout=5)
    if has_lock:
        try:
            payload = loader()
            if payload is not None:
                set_cached_sku(sku_code, payload, ttl=ttl)
            return payload
        finally:
            cache.delete(lock_key)

    for _ in range(5):
        time.sleep(0.05)
        cached = get_cached_sku(sku_code)
        if cached is not None:
            return cached
    return loader()
