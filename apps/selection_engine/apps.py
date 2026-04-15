from django.apps import AppConfig


class SelectionEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.selection_engine"
    verbose_name = "选品决策算法引擎"

    def ready(self) -> None:
        from . import signals  # noqa: F401
