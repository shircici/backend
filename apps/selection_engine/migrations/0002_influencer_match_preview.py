from django.db import migrations, models

import apps.selection_engine.models as selection_models


class Migration(migrations.Migration):
    dependencies = [
        ("selection_engine", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InfluencerMatchPreview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "batch_id",
                    models.CharField(db_index=True, help_text="一次批量任务 ID，可与 Redis 进度键对应", max_length=40),
                ),
                ("product_id", models.BigIntegerField(db_index=True)),
                (
                    "influencer_id",
                    models.CharField(db_index=True, help_text="达人侧主键（字符串兼容各平台）", max_length=64),
                ),
                (
                    "roas",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=20, null=True),
                ),
                ("grade", models.CharField(db_index=True, help_text="建议等级 A / B / C", max_length=1)),
                (
                    "detail",
                    models.JSONField(
                        blank=True,
                        default=selection_models.default_empty_dict,
                        help_text="测算入参快照或错误信息",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "selection_influencer_match_preview",
            },
        ),
        migrations.AddConstraint(
            model_name="influencermatchpreview",
            constraint=models.UniqueConstraint(fields=("batch_id", "influencer_id"), name="uniq_sel_prev_batch_inf"),
        ),
        migrations.AddIndex(
            model_name="influencermatchpreview",
            index=models.Index(fields=["batch_id", "product_id"], name="idx_sel_prev_batch_prod"),
        ),
    ]
