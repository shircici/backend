from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_shop_order_logistics"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountDeletionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_username", models.CharField(db_index=True, max_length=150)),
                ("anonymized_username", models.CharField(db_index=True, max_length=180)),
                ("reason", models.CharField(blank=True, default="", max_length=255)),
                ("deleted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deletion_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SmsDispatchLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone", models.CharField(db_index=True, max_length=32)),
                ("message_type", models.CharField(choices=[("sms", "SMS"), ("voice", "Voice")], default="sms", max_length=10)),
                ("provider", models.CharField(db_index=True, max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[("sending", "Sending"), ("delivered", "Delivered"), ("failed", "Failed")],
                        db_index=True,
                        default="sending",
                        max_length=20,
                    ),
                ),
                ("biz_id", models.CharField(blank=True, default="", max_length=128)),
                ("error_reason", models.CharField(blank=True, default="", max_length=255)),
                ("requested_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("delivered_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="PhoneRebindAppeal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_country_code", models.CharField(default="86", max_length=8)),
                ("current_phone_number", models.CharField(max_length=20)),
                ("requested_country_code", models.CharField(max_length=8)),
                ("requested_phone_number", models.CharField(max_length=20)),
                ("proof_material_urls", models.JSONField(blank=True, default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("reviewer", models.CharField(blank=True, default="", max_length=128)),
                ("review_note", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phone_rebind_appeals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UserPhoneBinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country_code", models.CharField(db_index=True, default="86", max_length=8)),
                ("phone_number", models.CharField(db_index=True, max_length=20)),
                ("is_primary", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="phone_binding",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("country_code", "phone_number")},
            },
        ),
        migrations.AddIndex(
            model_name="userphonebinding",
            index=models.Index(fields=["country_code", "phone_number"], name="core_userph_country_f7f9f5_idx"),
        ),
    ]
