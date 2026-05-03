from .settings import *  # noqa

# Integration tests: use external services via docker compose.
# Keep it close to production settings, but still deterministic.

DEBUG = False
DB_FAILOPEN_SQLITE = False
CACHE_FAILOPEN_LOCMEM = False

DATABASE_ROUTERS = []
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE", "sku_db"),
        "USER": os.getenv("MYSQL_USER", "backend"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", "backend_dev_pass"),
        "HOST": os.getenv("MYSQL_HOST", "mysql"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
CHANNEL_REDIS_URL = os.getenv("CHANNEL_REDIS_URL", "redis://redis:6379/2")

CELERY_TASK_ALWAYS_EAGER = True
