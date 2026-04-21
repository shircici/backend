from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True)),
                ("parent_id", models.BigIntegerField(db_index=True, default=0)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "category"},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_code", models.CharField(db_index=True, max_length=64, unique=True)),
                ("product_name", models.CharField(db_index=True, max_length=255)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="sku_mgt.category")),
            ],
            options={"db_table": "product"},
        ),
        migrations.CreateModel(
            name="Sku",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku_code", models.CharField(db_index=True, max_length=64)),
                ("product_name", models.CharField(db_index=True, max_length=255)),
                ("category_id", models.IntegerField(db_index=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("stock", models.IntegerField(default=0)),
                ("status", models.SmallIntegerField(db_index=True, default=1)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("version", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("product_id", models.BigIntegerField(db_index=True)),
            ],
            options={"db_table": "sku"},
        ),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["category", "is_deleted", "id"], name="idx_prod_cate_del_id")),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["updated_at", "id"], name="idx_prod_upd_id")),
        migrations.AddIndex(model_name="sku", index=models.Index(fields=["sku_code", "is_deleted"], name="idx_sku_code_del")),
        migrations.AddIndex(model_name="sku", index=models.Index(fields=["category_id", "status", "is_deleted", "id"], name="idx_sku_filter_page")),
        migrations.AddIndex(model_name="sku", index=models.Index(fields=["product_id", "is_deleted", "id"], name="idx_sku_prod_del_id")),
        migrations.AddIndex(model_name="sku", index=models.Index(fields=["updated_at", "id"], name="idx_sku_upd_id")),
        migrations.AddIndex(model_name="sku", index=models.Index(fields=["is_deleted", "created_at", "id"], name="idx_sku_del_create_id")),
        # 不在此处做 RANGE 分区：MySQL 要求分区键包含在主键中，而 Django 默认主键仅为 id。
        # 若生产需要分区，应改为 (created_at, id) 复合主键或单独运维脚本建表。
    ]
