from __future__ import annotations

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from .ws_notify import selection_ws_group


@database_sync_to_async
def _user_can_selection(user) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not getattr(settings, "RBAC_ENFORCE", False):
        return True
    groups = getattr(settings, "RBAC_SELECTION_ENGINE_GROUPS", ["selection_decision_maker", "management"])
    return user.groups.filter(name__in=groups).exists()


class SelectionBatchProgressConsumer(AsyncWebsocketConsumer):
    """
    订阅批量测算进度。连接示例::

        ws://<host>/ws/selection/batch/<batch_id>/?token=<JWT access>

    消息 JSON: {"type": "selection.progress", "data": {...}} 与 HTTP GET progress 字段一致。
    """

    async def connect(self):
        self.batch_id = self.scope["url_route"]["kwargs"]["batch_id"]
        user = self.scope.get("user") or AnonymousUser()
        if not await _user_can_selection(user):
            await self.close(code=4403)
            return
        self.group = selection_ws_group(self.batch_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self._send_snapshot()

    async def disconnect(self, close_code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def progress_push(self, event):
        await self.send(
            text_data=json.dumps({"type": "selection.progress", "data": event.get("payload") or {}}, ensure_ascii=False)
        )

    async def _send_snapshot(self):
        from .redis_progress import get_batch_progress

        snap = await database_sync_to_async(get_batch_progress)(self.batch_id)
        if snap:
            await self.send(
                text_data=json.dumps({"type": "selection.progress", "data": snap}, ensure_ascii=False)
            )
