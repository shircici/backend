from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("creator_mgt", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIAnalysisJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "job_type",
                    models.CharField(
                        choices=[("content_analysis", "content_analysis"), ("review_mining", "review_mining")],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "pending"), ("running", "running"), ("success", "success"), ("failed", "failed")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("input_payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_jobs",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "creator_ai_analysis_job", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="DataSyncJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "job_type",
                    models.CharField(
                        choices=[("profile_import", "profile_import"), ("audience_sync", "audience_sync"), ("ecom_sync", "ecom_sync")],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "pending"), ("running", "running"), ("success", "success"), ("failed", "failed")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sync_jobs",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "creator_data_sync_job", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="FulfillmentOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku_code", models.CharField(max_length=64)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("receiver_name", models.CharField(max_length=64)),
                ("receiver_phone", models.CharField(blank=True, max_length=32)),
                ("receiver_address", models.CharField(max_length=255)),
                ("logistics_provider", models.CharField(blank=True, max_length=64)),
                ("logistics_no", models.CharField(blank=True, max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "created"),
                            ("dispatched", "dispatched"),
                            ("in_transit", "in_transit"),
                            ("delivered", "delivered"),
                            ("exception", "exception"),
                        ],
                        default="created",
                        max_length=16,
                    ),
                ),
                ("tracking_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fulfillment_orders",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "creator_fulfillment_order", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(choices=[("email", "email"), ("whatsapp", "whatsapp"), ("instagram_dm", "instagram_dm")], max_length=32)),
                ("target_language", models.CharField(default="en", max_length=16)),
                ("pitch_text", models.TextField()),
                ("status", models.CharField(choices=[("draft", "draft"), ("sent", "sent"), ("failed", "failed")], default="draft", max_length=16)),
                ("provider_message_id", models.CharField(blank=True, max_length=128)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invitations",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "creator_invitation", "ordering": ["-id"]},
        ),
    ]
