"""
批量测算进度：写入 Redis Hash，供 HTTP 轮询或 WebSocket 推送进度百分比。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

PROGRESS_KEY_PREFIX = "selection_engine:batch:"


def batch_progress_key(batch_id: str) -> str:
    return f"{PROGRESS_KEY_PREFIX}{batch_id}"


def _conn():
    try:
        from django_redis import get_redis_connection
    except ImportError:
        return None
    return get_redis_connection("default")


def _decode(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        return val.decode()
    return str(val)


def init_batch_progress(batch_id: str, total: int, *, ttl_seconds: int = 86400) -> None:
    """初始化批次：total、done=0、status=running、percent=0。"""
    conn = _conn()
    if not conn:
        logger.warning("django_redis 不可用，跳过 Redis 进度初始化 batch_id=%s", batch_id)
        return
    key = batch_progress_key(batch_id)
    pipe = conn.pipeline()
    pipe.hset(
        key,
        mapping={
            "total": str(total),
            "done": "0",
            "status": "running",
            "percent": "0",
            "failed": "0",
        },
    )
    pipe.expire(key, ttl_seconds)
    pipe.execute()
    _push_ws(batch_id)


def mark_batch_empty_done(batch_id: str, *, ttl_seconds: int = 86400) -> None:
    conn = _conn()
    if not conn:
        return
    key = batch_progress_key(batch_id)
    pipe = conn.pipeline()
    pipe.hset(
        key,
        mapping={"total": "0", "done": "0", "status": "done", "percent": "100", "failed": "0"},
    )
    pipe.expire(key, ttl_seconds)
    pipe.execute()
    _push_ws(batch_id)


def increment_batch_progress(
    batch_id: str,
    *,
    failed: bool = False,
) -> dict[str, int | str]:
    """
    单个子任务结束时调用：原子递增 done；可选递增 failed；回写 percent。
    返回当前快照（total、done、percent、status、failed）。
    """
    conn = _conn()
    if not conn:
        return {"total": 0, "done": 0, "percent": 0, "status": "unknown", "failed": 0}

    key = batch_progress_key(batch_id)
    done = int(conn.hincrby(key, "done", 1))
    if failed:
        failed_n = int(conn.hincrby(key, "failed", 1))
    else:
        failed_n = int(_decode(conn.hget(key, "failed")) or 0)

    total = int(_decode(conn.hget(key, "total")) or 0)
    percent = 100 if total == 0 else min(100, int(done * 100 / total))
    status = "done" if total > 0 and done >= total else "running"

    conn.hset(key, mapping={"percent": str(percent), "status": status})
    snap = {"total": total, "done": done, "percent": percent, "status": status, "failed": failed_n}
    _push_ws(batch_id)
    return snap


def finalize_batch_status(batch_id: str, *, ttl_seconds: int = 86400) -> None:
    """chord 收尾：强制标记为 done、percent=100（与子任务递增互为兜底）。"""
    conn = _conn()
    if not conn:
        return
    key = batch_progress_key(batch_id)
    total = int(_decode(conn.hget(key, "total")) or 0)
    done = int(_decode(conn.hget(key, "done")) or 0)
    percent = 100 if total == 0 else min(100, int(done * 100 / total))
    pipe = conn.pipeline()
    pipe.hset(key, mapping={"status": "done", "percent": str(percent)})
    pipe.expire(key, ttl_seconds)
    pipe.execute()
    _push_ws(batch_id)


def _push_ws(batch_id: str) -> None:
    try:
        from .ws_notify import push_batch_progress

        push_batch_progress(batch_id)
    except Exception:  # noqa: BLE001
        logger.debug("WS 推送失败 batch_id=%s", batch_id, exc_info=True)


def get_batch_progress(batch_id: str) -> dict[str, Any]:
    """供 API 读取当前进度。"""
    conn = _conn()
    if not conn:
        return {}
    raw = conn.hgetall(batch_progress_key(batch_id))
    if not raw:
        return {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        key = _decode(k)
        val = _decode(v)
        if key in ("total", "done", "failed", "percent"):
            out[key] = int(val) if val != "" else 0
        else:
            out[key] = val
    return out
