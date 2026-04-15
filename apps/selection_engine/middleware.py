"""
WebSocket：从 query string 读取 JWT（token=），解析为 Django User 写入 scope。
"""
from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


def _token_from_scope(scope: dict) -> str | None:
    raw = scope.get("query_string") or b""
    if isinstance(raw, memoryview):
        raw = raw.tobytes()
    qs = parse_qs(raw.decode())
    vals = qs.get("token") or qs.get("access")
    return vals[0] if vals else None


@database_sync_to_async
def _user_from_jwt(token: str):
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.settings import api_settings
    from rest_framework_simplejwt.tokens import AccessToken

    User = get_user_model()
    try:
        access = AccessToken(token)
        uid = access[api_settings.USER_ID_CLAIM]
        if uid is None:
            return AnonymousUser()
        return User.objects.get(**{api_settings.USER_ID_FIELD: uid})
    except (User.DoesNotExist, TokenError, ValueError, TypeError, KeyError):
        return AnonymousUser()


class JwtAuthForWebSocketMiddleware:
    """仅处理 websocket scope，在 inner 前设置 scope['user']。"""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "websocket":
            return await self.inner(scope, receive, send)
        token = _token_from_scope(scope)
        if token:
            scope["user"] = await _user_from_jwt(token)
        else:
            scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)
