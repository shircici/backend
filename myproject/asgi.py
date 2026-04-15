"""
ASGI：HTTP 走 Django，WebSocket 走 Channels（选品批量进度推送）。
生产环境建议使用: daphne -b 0.0.0.0 -p 8000 myproject.asgi:application
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

django_asgi_app = get_asgi_application()

from apps.selection_engine.middleware import JwtAuthForWebSocketMiddleware  # noqa: E402
from apps.selection_engine.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JwtAuthForWebSocketMiddleware(URLRouter(websocket_urlpatterns))
        ),
    }
)
