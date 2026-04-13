import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "apps.common",
    "apps.core",
    "apps.sku_mgt",
    "apps.task_mgt",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.MetricsMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.common.middleware.SimpleRateLimitMiddleware",
    "apps.common.middleware.IdempotencyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"
ASGI_APPLICATION = "myproject.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "replace_me_db_name"),
        "USER": os.getenv("MYSQL_USER", "replace_me_db_user"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", "replace_me_db_password"),
        "HOST": os.getenv("MYSQL_HOST", "replace_me_db_host"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "120")),
        "OPTIONS": {
            "charset": "utf8mb4",
            "connect_timeout": 5,
            "read_timeout": 10,
            "write_timeout": 10,
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    },
    "read_replica": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_REPLICA_DATABASE", os.getenv("MYSQL_DATABASE", "replace_me_db_name")),
        "USER": os.getenv("MYSQL_REPLICA_USER", os.getenv("MYSQL_USER", "replace_me_db_user")),
        "PASSWORD": os.getenv("MYSQL_REPLICA_PASSWORD", os.getenv("MYSQL_PASSWORD", "replace_me_db_password")),
        "HOST": os.getenv("MYSQL_REPLICA_HOST", os.getenv("MYSQL_HOST", "replace_me_db_host")),
        "PORT": os.getenv("MYSQL_REPLICA_PORT", os.getenv("MYSQL_PORT", "3306")),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "120")),
        "OPTIONS": {
            "charset": "utf8mb4",
            "connect_timeout": 5,
        },
    },
}

DATABASE_ROUTERS = ["myproject.db_router.ReadWriteRouter"]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://replace_me_redis_host:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 3,
            "SOCKET_TIMEOUT": 3,
            "CONNECTION_POOL_KWARGS": {"max_connections": 200, "retry_on_timeout": True},
        },
    }
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.sku_mgt.pagination.SkuCursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").strip()
SPECTACULAR_SERVERS = []
if BACKEND_PUBLIC_URL:
    SPECTACULAR_SERVERS = [
        {"url": BACKEND_PUBLIC_URL.rstrip("/"), "description": "后端 API 基地址（前端联调用）"},
    ]

SPECTACULAR_SETTINGS = {
    "TITLE": "多平台商品采集与库存同步系统",
    "DESCRIPTION": (
        "API 契约：路径、方法、请求/响应 JSON 均以本 OpenAPI 为准；"
        "禁止仅以口头或即时消息传递接口 JSON。"
    ),
    "VERSION": "1.0.0",
    "SERVERS": SPECTACULAR_SERVERS,
}

# RBAC：基于 Django Group；生产环境建议 RBAC_ENFORCE=true
RBAC_ENFORCE = os.getenv("RBAC_ENFORCE", "false").lower() == "true"
RBAC_API_INTEGRATOR_GROUPS = [
    g.strip()
    for g in os.getenv("RBAC_API_INTEGRATOR_GROUPS", "api_integrator").split(",")
    if g.strip()
]

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://replace_me_redis_host:6379/1")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://replace_me_redis_host:6379/1")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
CELERY_BEAT_SCHEDULE = {
    "refresh-platform-tokens-every-10-min": {
        "task": "apps.core.tasks.refresh_expiring_tokens",
        "schedule": 600,
    },
    "inventory-sync-every-5-min": {
        "task": "apps.core.tasks.scheduled_inventory_sync",
        "schedule": 300,
    },
    "daily-sku-export": {
        "task": "apps.sku_mgt.tasks.export_sku_to_csv",
        "schedule": 86400,
    },
}

FERNET_KEY = os.getenv("FERNET_KEY", "")
OPS_ADMIN_USERNAMES = [name.strip() for name in os.getenv("OPS_ADMIN_USERNAMES", "admin").split(",") if name.strip()]

# 开发服务端口（文档约定；runserver 命令行可覆盖）
DJANGO_RUNSERVER_PORT = os.getenv("DJANGO_RUNSERVER_PORT", "8000")

CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "True").lower() == "true"
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if not CORS_ALLOW_ALL_ORIGINS else []

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        },
        "simple": {"format": "%(asctime)s %(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.getenv("DB_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
    },
}
