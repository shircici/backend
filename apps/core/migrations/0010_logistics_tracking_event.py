from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_order_status_signed"),
    ]

    operations = [
        migrations.CreateModel(
            name="LogisticsTrackingEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_time", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("event_time_raw", models.CharField(blank=True, default="", max_length=64)),
                ("status", models.CharField(blank=True, default="", max_length=255)),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("source", models.CharField(db_index=True, default="webhook", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "shipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tracking_events",
                        to="core.logisticsshipment",
                    ),
                ),
            ],
            options={
                "unique_together": {("shipment", "event_time_raw", "status", "location", "source")},
                "indexes": [models.Index(fields=["shipment", "event_time", "source"], name="core_logist_shipment_4c2c9f_idx")],
            },
        ),
    ]

