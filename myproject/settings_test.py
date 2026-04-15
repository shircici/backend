from .settings import *  # noqa

# Fast and dependency-light test DB.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable read replica and routers for isolated test run.
DATABASE_ROUTERS = []

# Keep tests deterministic and fast.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
# 单测不等待真实发送间隔
SMS_SEND_MIN_INTERVAL_SECONDS = 0
SMS_SEND_IP_MIN_INTERVAL_SECONDS = 0
SMS_SEND_DAILY_LIMIT_PHONE = 0
SMS_CAPTCHA_REQUIRED = False
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
ASGI_APPLICATION = "myproject.asgi.application"
