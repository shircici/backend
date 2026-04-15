"""
WebSocket 进度推送：通过 Channels group 广播与 Redis Hash 一致的进度快照。
"""
from __future__ import annotations

import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def selection_ws_group(batch_id: str) -> str:
    return f"selection_batch_{batch_id}"


def push_batch_progress(batch_id: str) -> None:
    try:
        from .redis_progress import get_batch_progress

        layer = get_channel_layer()
        if layer is None:
            return
        payload = get_batch_progress(batch_id)
        if not payload:
            return
        message = {"type": "progress_push", "payload": payload}
        async_to_sync(layer.group_send)(selection_ws_group(batch_id), message)
    except Exception as exc:  # noqa: BLE001
        logger.debug("WebSocket 进度推送跳过 batch_id=%s: %s", batch_id, exc)
