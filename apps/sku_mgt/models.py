from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=64, unique=True)
    parent_id = models.BigIntegerField(default=0, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "category"


class Product(models.Model):
    product_code = models.CharField(max_length=64, unique=True, db_index=True)
    product_name = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product"
        indexes = [
            models.Index(fields=["category", "is_deleted", "id"], name="idx_prod_cate_del_id"),
            models.Index(fields=["updated_at", "id"], name="idx_prod_upd_id"),
        ]


class Sku(models.Model):
    """
    10M+ SKU optimization notes:
    1) Keep hot filters covered by composite indexes.
    2) Soft delete via is_deleted to avoid heavy physical deletion.
    3) Prefer keyset pagination by (id, created_at) instead of large OFFSET.
    4) Production partitioning suggestion (MySQL):
       - RANGE partition by created_at month
       - or HASH partition by category_id / merchant_id.
       Use raw SQL migration for partitioning in production.
    """

    sku_code = models.CharField(max_length=64, db_index=True)
    product_id = models.BigIntegerField(db_index=True)
    product_name = models.CharField(max_length=255, db_index=True)
    category_id = models.IntegerField(db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="采购/供货成本；为空时选品引擎可回退为售价比例估算",
    )
    stock = models.IntegerField(default=0)
    status = models.SmallIntegerField(default=1, db_index=True)  # 1:on sale, 0:off shelf
    is_deleted = models.BooleanField(default=False, db_index=True)
    version = models.IntegerField(default=0)  # optimistic lock version
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "sku"
        indexes = [
            models.Index(fields=["sku_code", "is_deleted"], name="idx_sku_code_del"),
            models.Index(fields=["category_id", "status", "is_deleted", "id"], name="idx_sku_filter_page"),
            models.Index(fields=["product_id", "is_deleted", "id"], name="idx_sku_prod_del_id"),
            models.Index(fields=["updated_at", "id"], name="idx_sku_upd_id"),
            models.Index(fields=["is_deleted", "created_at", "id"], name="idx_sku_del_create_id"),
            # MySQL fulltext needs raw SQL migration in some versions/engines.
        ]
