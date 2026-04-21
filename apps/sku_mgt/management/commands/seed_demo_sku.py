from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sku_mgt.models import Category, Product, Sku


class Command(BaseCommand):
    help = "导入本地演示 SKU 数据，便于接口/网页联调查看。"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5, help="要创建的演示 SKU 数量")

    def handle(self, *args, **options):
        count = max(1, min(int(options["count"]), 50))
        created = 0
        updated = 0

        with transaction.atomic():
            category, _ = Category.objects.get_or_create(
                name="演示分类",
                defaults={"parent_id": 0},
            )
            product, _ = Product.objects.get_or_create(
                product_code="DEMO-PRODUCT-001",
                defaults={
                    "product_name": "演示商品（用于数据库连通验证）",
                    "category": category,
                },
            )

            for i in range(1, count + 1):
                sku_code = f"DEMO-SKU-{i:03d}"
                _, was_created = Sku.objects.update_or_create(
                    sku_code=sku_code,
                    defaults={
                        "product_id": product.id,
                        "product_name": product.product_name,
                        "category_id": category.id,
                        "price": Decimal("99.00") + i,
                        "cost": Decimal("50.00") + i,
                        "stock": 100 + i,
                        "status": 1,
                        "is_deleted": False,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_demo_sku completed: category_id={category.id}, product_id={product.id}, created={created}, updated={updated}"
            )
        )
