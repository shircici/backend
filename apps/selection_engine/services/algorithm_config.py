from __future__ import annotations

from decimal import Decimal

from django.core.cache import cache

from ..models import AlgorithmConfig


def _thresholds_from_db() -> dict[str, str]:
    row = AlgorithmConfig.objects.filter(is_active=True).order_by("-updated_at").first()
    if not row or not row.thresholds:
        return {"min_roas": "3", "ideal_roas": "5"}
    t = row.thresholds
    return {
        "min_roas": str(t.get("min_roas", 3)),
        "ideal_roas": str(t.get("ideal_roas", 5)),
    }


def get_active_thresholds() -> tuple[Decimal, Decimal]:
    """
    读取当前生效的 min_roas / ideal_roas；使用 cache.get_or_set 降低数据库 IO。
    """
    raw = cache.get_or_set("selection_engine:algo_thresholds:v1", _thresholds_from_db, timeout=300)
    return Decimal(raw["min_roas"]), Decimal(raw["ideal_roas"])


def invalidate_threshold_cache() -> None:
    cache.delete("selection_engine:algo_thresholds:v1")
