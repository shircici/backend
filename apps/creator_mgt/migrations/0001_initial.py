from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Creator",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform_uid", models.CharField(max_length=64, unique=True)),
                ("handle", models.CharField(max_length=64)),
                ("region", models.CharField(blank=True, max_length=32)),
                ("tier", models.CharField(blank=True, max_length=16)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("whatsapp", models.CharField(blank=True, max_length=32)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "creator", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="CreatorAIInsight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("style_tags", models.JSONField(blank=True, default=list)),
                ("competitor_products_json", models.JSONField(blank=True, default=list)),
                ("sentiment_keywords_json", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_insight",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "creator_ai_insight", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="CreatorEcomProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("audience_age_json", models.JSONField(blank=True, default=dict)),
                ("audience_gender_json", models.JSONField(blank=True, default=dict)),
                ("amazon_storefront_url", models.URLField(blank=True)),
                ("tiktok_shop_gpm", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("trend_timeseries_json", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ecom_profile",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "creator_ecom_profile", "ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="FulfillmentAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sample_status", models.CharField(default="pending", max_length=32)),
                ("logistics_no", models.CharField(blank=True, max_length=64)),
                ("logistics_status", models.CharField(blank=True, max_length=32)),
                ("tiktok_auth_code", models.CharField(blank=True, max_length=256)),
                ("asset_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fulfillments",
                        to="creator_mgt.creator",
                    ),
                ),
            ],
            options={"db_table": "fulfillment_asset", "ordering": ["-id"]},
        ),
    ]
