from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_replay_audit_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("order_no", models.CharField(db_index=True, max_length=128, unique=True)),
                ("buyer_name", models.CharField(blank=True, default="", max_length=128)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("shipped", "Shipped"), ("completed", "Completed"), ("cancelled", "Cancelled")], db_index=True, default="pending", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name="Shop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("external_shop_id", models.CharField(max_length=128, unique=True)),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("status", models.CharField(db_index=True, default="active", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="LogisticsShipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("waybill_no", models.CharField(db_index=True, max_length=128, unique=True)),
                ("carrier", models.CharField(default="mock-express", max_length=64)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("in_transit", "In Transit"), ("delivered", "Delivered"), ("exception", "Exception")], db_index=True, default="pending", max_length=20)),
                ("latest_event", models.CharField(blank=True, default="", max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shipments", to="core.order")),
            ],
        ),
    ]
