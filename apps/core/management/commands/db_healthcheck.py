from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "检查 MySQL 连接，可选执行一次读写事务。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-write",
            action="store_true",
            help="执行一次轻量写入事务（创建临时表并回滚）",
        )

    def handle(self, *args, **options):
        with_write = options["with_write"]
        db_settings = connection.settings_dict
        self.stdout.write(
            f"DB target: {db_settings.get('HOST')}:{db_settings.get('PORT')} / {db_settings.get('NAME')}"
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION(), DATABASE()")
                version, current_db = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(f"MySQL connected: version={version}, database={current_db}"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"MySQL connect failed: {exc}"))
            raise SystemExit(1)

        if not with_write:
            self.stdout.write(self.style.SUCCESS("db_healthcheck passed (read-only mode)"))
            return

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 使用临时表，避免污染业务数据；事务结束自动回滚验证写能力。
                    cursor.execute("CREATE TEMPORARY TABLE IF NOT EXISTS db_healthcheck_tmp (id INT)")
                    cursor.execute("INSERT INTO db_healthcheck_tmp (id) VALUES (1)")
                    cursor.execute("SELECT COUNT(*) FROM db_healthcheck_tmp")
                    count = cursor.fetchone()[0]
                    if count != 1:
                        raise RuntimeError("temporary table insert check failed")
                    raise RuntimeError("force rollback for write check")
        except RuntimeError as exc:
            if str(exc) == "force rollback for write check":
                self.stdout.write(self.style.SUCCESS("write transaction check passed (rolled back)"))
            else:
                self.stdout.write(self.style.ERROR(f"write transaction check failed: {exc}"))
                raise SystemExit(1)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"write transaction check failed: {exc}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("db_healthcheck passed (read+write mode)"))
