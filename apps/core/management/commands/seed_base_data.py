from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import (
    CollectionTask,
    InventoryAdjustment,
    InventorySyncLog,
    LogisticsRateCard,
    LogisticsShipment,
    LogisticsTrackingEvent,
    Order,
    OrderRemark,
    PlatformToken,
    Product,
    ProductVariant,
    Shop,
    Warehouse,
)
from apps.sku_mgt.models import Category, Product as SkuProduct, Sku


class Command(BaseCommand):
    help = "Seed base production-like data for interface verification."

    def handle(self, *args, **options):
        User = get_user_model()
        with transaction.atomic():
            category, _ = Category.objects.get_or_create(name="跨境爆品", defaults={"parent_id": 0})
            sku_product, _ = SkuProduct.objects.get_or_create(
                product_code="SKU-DEMO-001",
                defaults={"product_name": "跨境演示商品", "category": category},
            )
            product, _ = Product.objects.get_or_create(
                platform="amazon",
                platform_product_id="AMZ-DEMO-001",
                defaults={
                    "title": "跨境演示商品",
                    "images": ["https://example.com/demo-1.jpg"],
                    "attributes": {"color": "black", "size": "M"},
                    "price": Decimal("29.90"),
                    "stock": 128,
                },
            )
            ProductVariant.objects.get_or_create(
                product=product,
                sku="AMZ-DEMO-001-RED",
                defaults={"title": "跨境演示商品 - 红色", "price": Decimal("31.90"), "stock": 64, "attributes": {"color": "red"}},
            )
            Sku.objects.get_or_create(
                sku_code="SKU-DEMO-001",
                defaults={"product_id": sku_product.id, "product_name": sku_product.product_name, "category_id": category.id, "price": Decimal("29.90"), "cost": Decimal("16.80"), "stock": 128, "status": 1},
            )
            warehouse, _ = Warehouse.objects.get_or_create(
                code="SZ-001",
                defaults={"name": "深圳前海仓", "address": {"country": "CN", "city": "深圳"}, "status": "active"},
            )
            Shop.objects.get_or_create(external_shop_id="shop-amz-001", defaults={"platform": "amazon", "name": "Amazon Demo Shop", "status": "active"})
            LogisticsRateCard.objects.get_or_create(
                carrier="YTO",
                destination_country="US",
                defaults={"base_weight_kg": Decimal("0.50"), "base_price": Decimal("48.00"), "additional_price_per_kg": Decimal("18.00"), "currency": "CNY", "is_active": True},
            )
            order1, _ = Order.objects.get_or_create(
                platform="amazon",
                order_no="AMZ202605030001",
                defaults={"buyer_name": "Alice", "status": Order.STATUS_PAID, "amount": Decimal("59.80"), "recipient_name": "Alice", "recipient_phone": "13800000001", "shipping_address": {"country": "US", "city": "Los Angeles"}},
            )
            LogisticsShipment.objects.get_or_create(order=order1, waybill_no="WB202605030001", defaults={"carrier": "YTO", "status": LogisticsShipment.STATUS_DELIVERED, "latest_event": "已签收"})
            LogisticsTrackingEvent.objects.get_or_create(shipment=LogisticsShipment.objects.get(order=order1), event_time_raw="2026-05-03T09:00:00+08:00", status="已签收", location="Los Angeles", source="seed", defaults={"event_time": None, "raw_payload": {"seed": True}})
            InventorySyncLog.objects.get_or_create(platform="amazon", warehouse_id=warehouse.code, defaults={"total_items": 2, "success_count": 2, "fail_count": 0, "message": "seeded"})
            InventoryAdjustment.objects.get_or_create(sku="SKU-DEMO-001", warehouse=warehouse, defaults={"product": SkuProduct.objects.first(), "adjustment_type": "increase", "quantity": 20, "reason": "初始铺货", "operator": "system"})
            OrderRemark.objects.get_or_create(order=order1, content="已确认收款，等待发货。", defaults={"operator": "system"})
            CollectionTask.objects.get_or_create(platform="amazon", status="running", defaults={"target_ids": ["AMZ-DEMO-001"], "result_message": "同步中"})
            PlatformToken.objects.get_or_create(platform="amazon", account_id="default", defaults={"access_token_encrypted": "enc-access", "refresh_token_encrypted": "enc-refresh", "expires_at": "2030-01-01T00:00:00Z"})
            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(username="admin", password="Admin123456")

        self.stdout.write(self.style.SUCCESS("seed_base_data completed"))
