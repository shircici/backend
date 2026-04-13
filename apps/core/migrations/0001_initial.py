from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CollectionTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("target_ids", models.JSONField(default=list)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("success", "Success"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("result_message", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name="InventorySyncLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("warehouse_id", models.CharField(db_index=True, max_length=64)),
                ("total_items", models.IntegerField(default=0)),
                ("success_count", models.IntegerField(default=0)),
                ("fail_count", models.IntegerField(default=0)),
                ("message", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name="PlatformToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("account_id", models.CharField(db_index=True, default="default", max_length=128)),
                ("access_token_encrypted", models.TextField()),
                ("refresh_token_encrypted", models.TextField()),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"unique_together": {("platform", "account_id")}},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("platform_product_id", models.CharField(db_index=True, max_length=128)),
                ("title", models.CharField(max_length=500)),
                ("images", models.JSONField(blank=True, default=list)),
                ("attributes", models.JSONField(blank=True, default=dict)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("stock", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"unique_together": {("platform", "platform_product_id")}},
        ),
        migrations.CreateModel(
            name="SyncRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(choices=[("tiktok", "TikTok Shop"), ("amazon", "Amazon"), ("1688", "1688")], db_index=True, max_length=20)),
                ("warehouse_id", models.CharField(db_index=True, max_length=64)),
                ("sync_enabled", models.BooleanField(db_index=True, default=True)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"unique_together": {("platform", "warehouse_id")}},
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(db_index=True, max_length=128)),
                ("title", models.CharField(max_length=255)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("stock", models.IntegerField(default=0)),
                ("attributes", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="core.product")),
            ],
        ),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["platform", "platform_product_id"], name="core_produc_platfor_70041e_idx")),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["platform", "updated_at"], name="core_produc_platfor_80f80f_idx")),
        migrations.AddIndex(model_name="productvariant", index=models.Index(fields=["product", "sku"], name="core_produc_product_434761_idx")),
    ]
