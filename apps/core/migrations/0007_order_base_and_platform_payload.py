from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_device_phone_relation"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="order",
            options={
                "permissions": (("order_edit", "Can manually edit order address"),),
            },
        ),
        migrations.AlterField(
            model_name="order",
            name="order_no",
            field=models.CharField(db_index=True, max_length=128),
        ),
        migrations.AddField(
            model_name="order",
            name="recipient_name",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="order",
            name="recipient_phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_address",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterUniqueTogether(
            name="order",
            unique_together={("platform", "order_no")},
        ),
        migrations.CreateModel(
            name="PlatformOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("platform_order_id", models.CharField(db_index=True, max_length=128)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("synced_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="platform_payloads", to="core.order")),
            ],
            options={
                "unique_together": {("platform", "platform_order_id")},
            },
        ),
        migrations.AddIndex(
            model_name="platformorder",
            index=models.Index(fields=["order", "platform", "synced_at"], name="core_platfo_order_i_a09be5_idx"),
        ),
    ]
