from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import apps.selection_engine.models as selection_models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AlgorithmConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, default="default", help_text="配置编码，用于缓存键与多环境切换", max_length=64, unique=True)),
                ("name", models.CharField(blank=True, default="", max_length=128)),
                (
                    "thresholds",
                    models.JSONField(
                        default=selection_models.default_algorithm_thresholds,
                        help_text="如 min_roas、ideal_roas 等",
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "selection_algorithm_config",
            },
        ),
        migrations.CreateModel(
            name="DecisionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_id", models.BigIntegerField(db_index=True, help_text="业务侧商品主键")),
                (
                    "input_params",
                    models.JSONField(
                        default=selection_models.default_empty_dict,
                        help_text="前端/WMS 等参与计算的原始入参",
                    ),
                ),
                ("roas", models.DecimalField(decimal_places=6, help_text="计算得到的 ROAS", max_digits=20)),
                ("decision_label", models.CharField(db_index=True, help_text="决策标签，如 PASS / HOLD / REJECT", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="selection_decision_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "selection_decision_log",
            },
        ),
        migrations.AddIndex(
            model_name="algorithmconfig",
            index=models.Index(fields=["is_active", "code"], name="idx_sel_algo_act_code"),
        ),
        migrations.AddIndex(
            model_name="decisionlog",
            index=models.Index(fields=["user", "created_at"], name="idx_sel_dlog_user_ct"),
        ),
        migrations.AddIndex(
            model_name="decisionlog",
            index=models.Index(fields=["product_id", "created_at"], name="idx_sel_dlog_prod_ct"),
        ),
    ]
