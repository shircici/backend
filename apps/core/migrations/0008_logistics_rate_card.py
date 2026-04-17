from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_order_base_and_platform_payload"),
    ]

    operations = [
        migrations.CreateModel(
            name="LogisticsRateCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("carrier", models.CharField(db_index=True, max_length=64)),
                ("destination_country", models.CharField(db_index=True, max_length=8)),
                ("base_weight_kg", models.DecimalField(decimal_places=3, default=0.5, max_digits=8)),
                ("base_price", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("additional_price_per_kg", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("currency", models.CharField(default="CNY", max_length=8)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="logisticsratecard",
            index=models.Index(fields=["carrier", "destination_country", "is_active"], name="core_logist_carrier_4b834f_idx"),
        ),
    ]
