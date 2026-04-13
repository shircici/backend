import os

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Run preflight checks before deployment/startup."

    def handle(self, *args, **options):
        required_env = [
            "DJANGO_SECRET_KEY",
            "MYSQL_DATABASE",
            "MYSQL_USER",
            "MYSQL_PASSWORD",
            "MYSQL_HOST",
            "MYSQL_PORT",
            "REDIS_URL",
            "FERNET_KEY",
        ]

        missing = [key for key in required_env if not os.getenv(key)]
        if missing:
            self.stdout.write(self.style.ERROR(f"missing env vars: {missing}"))
        else:
            self.stdout.write(self.style.SUCCESS("env vars check passed"))

        db_ok = False
        cache_ok = False

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_ok = True
            self.stdout.write(self.style.SUCCESS("database check passed"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"database check failed: {exc}"))

        try:
            cache.set("preflight:ping", "pong", timeout=10)
            cache_ok = cache.get("preflight:ping") == "pong"
            if cache_ok:
                self.stdout.write(self.style.SUCCESS("cache check passed"))
            else:
                self.stdout.write(self.style.ERROR("cache check failed: ping mismatch"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"cache check failed: {exc}"))

        self.stdout.write(f"ops admin usernames={getattr(settings, 'OPS_ADMIN_USERNAMES', [])}")

        if missing or not db_ok or not cache_ok:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("preflight_check passed"))
