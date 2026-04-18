from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.common.metrics import metrics_view

# OpenAPI / 文档页必须匿名可访问，便于前端 B 拉取契约（不受 DEFAULT_PERMISSION_CLASSES 影响）
_SCHEMA_AUTH = {"permission_classes": [AllowAny], "authentication_classes": []}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(**_SCHEMA_AUTH), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema", **_SCHEMA_AUTH), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema", **_SCHEMA_AUTH), name="redoc"),
    path("metrics", metrics_view, name="metrics"),
    path("api/", include("apps.core.urls")),
    # v1：对外联调固定前缀（例如 17Track Webhook 回调）
    path("v1/", include("apps.core.urls")),
    path("api/", include("apps.creator_mgt.urls")),
    path("api/sku/", include("apps.sku_mgt.urls")),
    path("api/", include("apps.task_mgt.urls")),
    path("api/", include("apps.selection_engine.urls")),
]
