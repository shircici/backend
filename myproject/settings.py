import os
from pathlib import Path
from datetime import timedelta

from kombu import Exchange, Queue

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "apps.common",
    "apps.core",
    "apps.creator_mgt",
    "apps.sku_mgt",
    "apps.task_mgt",
    "apps.selection_engine",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.MetricsMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.common.middleware.GlobalSmsCircuitBreakerMiddleware",
    "apps.common.middleware.SimpleRateLimitMiddleware",
    "apps.common.middleware.IdempotencyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.SensitiveDataMaskingMiddleware",
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

# Django Channels（WebSocket）；默认使用独立 Redis DB，避免与 CACHES 键冲突
CHANNEL_REDIS_URL = os.getenv("CHANNEL_REDIS_URL", "redis://replace_me_redis_host:6379/2")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CHANNEL_REDIS_URL],
        },
    },
}
ASGI_APPLICATION = "myproject.asgi.application"

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
# 选品决策算法引擎：Django Group 名称（与 create_rbac_groups 一致）
RBAC_SELECTION_ENGINE_GROUPS = [
    g.strip()
    for g in os.getenv("RBAC_SELECTION_ENGINE_GROUPS", "selection_decision_maker,management").split(",")
    if g.strip()
]
# 单次测算默认平台佣金率（0~1），前端未传 commission_rate 时使用
SELECTION_DEFAULT_COMMISSION_RATE = os.getenv("SELECTION_DEFAULT_COMMISSION_RATE", "0.08")

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://replace_me_redis_host:6379/1")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://replace_me_redis_host:6379/1")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
TIKTOK_ORDER_POLL_MINUTES = int(os.getenv("TIKTOK_ORDER_POLL_MINUTES", "20"))
if TIKTOK_ORDER_POLL_MINUTES < 10:
    TIKTOK_ORDER_POLL_MINUTES = 10
if TIKTOK_ORDER_POLL_MINUTES > 30:
    TIKTOK_ORDER_POLL_MINUTES = 30
TIKTOK_ORDERLIST_PAGE_SIZE = int(os.getenv("TIKTOK_ORDERLIST_PAGE_SIZE", "50"))
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
    "poll-tiktok-orders": {
        "task": "apps.core.tasks.schedule_tiktok_order_polling",
        "schedule": TIKTOK_ORDER_POLL_MINUTES * 60,
    },
}

# Celery 队列：选品/达人测算走独立队列，便于扩容与限流
_default_exchange = Exchange("default", type="direct")
_selection_exchange = Exchange("selection", type="direct")
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = (
    Queue("default", _default_exchange, routing_key="default"),
    Queue("selection", _selection_exchange, routing_key="selection"),
)
CELERY_TASK_ROUTES = {
    "apps.selection_engine.tasks.batch_calculate_influencer_roas": {"queue": "selection"},
    "apps.selection_engine.tasks.calculate_single_influencer_roas": {"queue": "selection"},
    "apps.selection_engine.tasks.finalize_influencer_batch": {"queue": "selection"},
}

FERNET_KEY = os.getenv("FERNET_KEY", "")
OPS_ADMIN_USERNAMES = [name.strip() for name in os.getenv("OPS_ADMIN_USERNAMES", "admin").split(",") if name.strip()]
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "aliyun").strip().lower()
SMS_CODE_TTL_SECONDS = int(os.getenv("SMS_CODE_TTL_SECONDS", "300"))
# 同一手机号两次「发送成功」之间的最短间隔（秒）
SMS_SEND_MIN_INTERVAL_SECONDS = int(os.getenv("SMS_SEND_MIN_INTERVAL_SECONDS", "60"))
# 校验失败达到此次数后锁定该手机号一段时间（防爆破）
SMS_VERIFY_MAX_FAILURES = int(os.getenv("SMS_VERIFY_MAX_FAILURES", "5"))
# 校验失败过多后的锁定时长（秒）
SMS_VERIFY_LOCK_SECONDS = int(os.getenv("SMS_VERIFY_LOCK_SECONDS", "900"))
# 同一手机号自然日内最多发送短信次数（0 表示不限制）
SMS_SEND_DAILY_LIMIT_PHONE = int(os.getenv("SMS_SEND_DAILY_LIMIT_PHONE", "5"))
# 同一 IP 两次发送之间的最短间隔（秒），用于防轰炸；0 表示不限制
SMS_SEND_IP_MIN_INTERVAL_SECONDS = int(os.getenv("SMS_SEND_IP_MIN_INTERVAL_SECONDS", "60"))
# 发送短信前是否必须校验图形验证码（人机挑战）
SMS_CAPTCHA_REQUIRED = os.getenv("SMS_CAPTCHA_REQUIRED", "False").lower() == "true"
SMS_GLOBAL_HOURLY_LIMIT = int(os.getenv("SMS_GLOBAL_HOURLY_LIMIT", "10000"))
DEVICE_PHONE_DAILY_LIMIT = int(os.getenv("DEVICE_PHONE_DAILY_LIMIT", "5"))
SMS_PROVIDER_CHAIN = [i.strip() for i in os.getenv("SMS_PROVIDER_CHAIN", "aliyun,tencent,mock").split(",") if i.strip()]
ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
ALIYUN_SMS_SIGN_NAME = os.getenv("ALIYUN_SMS_SIGN_NAME", "")
ALIYUN_SMS_TEMPLATE_CODE = os.getenv("ALIYUN_SMS_TEMPLATE_CODE", "")
ALIYUN_SMS_ENDPOINT = os.getenv("ALIYUN_SMS_ENDPOINT", "dysmsapi.aliyuncs.com")
ALIYUN_SMS_REGION = os.getenv("ALIYUN_SMS_REGION", "cn-hangzhou")

# TikTok 授权（达人检索）
TIKTOK_CREATOR_APP_KEY = os.getenv("TIKTOK_CREATOR_APP_KEY", "")
TIKTOK_CREATOR_APP_SECRET = os.getenv("TIKTOK_CREATOR_APP_SECRET", "")
TIKTOK_OAUTH_TOKEN_URL = os.getenv("TIKTOK_OAUTH_TOKEN_URL", "https://open.tiktokapis.com/v2/oauth/token/")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "")
TIKTOK_SCOPES = os.getenv("TIKTOK_SCOPES", "user.info.basic,video.list")
TIKTOK_AUTH_BASE_URL = os.getenv("TIKTOK_AUTH_BASE_URL", "https://www.tiktok.com/v2/auth/authorize/")
TIKTOK_API_BASE_URL = os.getenv("TIKTOK_API_BASE_URL", "https://open.tiktokapis.com/v2/")

# 物流聚合（17Track / 快递100）
LOGISTICS_AGGREGATOR_PROVIDER = os.getenv("LOGISTICS_AGGREGATOR_PROVIDER", "17track")
LOGISTICS_WEBHOOK_TOKEN = os.getenv("LOGISTICS_WEBHOOK_TOKEN", "")
LOGISTICS_VOLUME_DIVISOR = int(os.getenv("LOGISTICS_VOLUME_DIVISOR", "6000"))
TRACK17_API_KEY = os.getenv("TRACK17_API_KEY", "")
TRACK17_API_BASE_URL = os.getenv("TRACK17_API_BASE_URL", "https://api.17track.net/track/v2")
KUAIDI100_API_KEY = os.getenv("KUAIDI100_API_KEY", "")
KUAIDI100_TRACK_URL = os.getenv("KUAIDI100_TRACK_URL", "https://poll.kuaidi100.com/poll/query.do")

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
        "auth_file": {
            "class": "logging.FileHandler",
            "formatter": "standard",
            "filename": os.getenv("AUTH_AUDIT_LOG_FILE", str(BASE_DIR / "auth_audit.log")),
        },
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.getenv("DB_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "apps.core.auth": {
            "handlers": ["console", "auth_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
