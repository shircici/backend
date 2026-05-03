from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import (
    InventoryAdjustment,
    InventorySyncLog,
    LogisticsShipment,
    LogisticsTrackingEvent,
    Order,
    Product,
    ProductVariant,
    Warehouse,
)
from apps.sku_mgt.models import Product as SkuProduct, Sku


class Command(BaseCommand):
    help = "Seed boundary-case data for edge case verification."

    def handle(self, *args, **options):
        with transaction.atomic():
            empty_warehouse, _ = Warehouse.objects.get_or_create(
                code="EMPTY-001",
                defaults={"name": "空仓库", "address": {"country": "CN", "city": "东莞"}, "status": "active"},
            )
            low_stock_product, _ = Product.objects.get_or_create(
                platform="1688",
                platform_product_id="A-DEMO-003",
                defaults={
                    "title": "低库存演示商品",
                    "images": ["https://example.com/demo-3.jpg"],
                    "attributes": {"color": "blue"},
                    "price": Decimal("19.90"),
                    "stock": 3,
                },
            )
            ProductVariant.objects.get_or_create(
                product=low_stock_product,
                sku="A-DEMO-003-BL",
                defaults={"title": "低库存演示商品 - 蓝色", "price": Decimal("21.90"), "stock": 3, "attributes": {"color": "blue"}},
            )
            SkuProduct.objects.get_or_create(
                product_code="SKU-DEMO-004-PROD",
                defaults={"product_name": "低库存演示商品", "category_id": 1},
            )
            Sku.objects.get_or_create(
                sku_code="SKU-DEMO-004",
                defaults={"product_id": 1, "product_name": "低库存演示商品", "category_id": 1, "price": Decimal("19.90"), "cost": Decimal("8.90"), "stock": 3, "status": 1},
            )
            order, _ = Order.objects.get_or_create(
                platform="1688",
                order_no="A202605030003",
                defaults={
                    "buyer_name": "Cathy",
                    "status": Order.STATUS_CANCELLED,
                    "amount": Decimal("0.00"),
                    "recipient_name": "Cathy",
                    "recipient_phone": "13800000003",
                    "shipping_address": {"country": "CN", "city": "Shenzhen"},
                },
            )
            shipment, _ = LogisticsShipment.objects.get_or_create(
                order=order,
                waybill_no="WB202605030003",
                defaults={"carrier": "JD", "status": LogisticsShipment.STATUS_EXCEPTION, "latest_event": "地址异常"},
            )
            LogisticsTrackingEvent.objects.get_or_create(
                shipment=shipment,
                event_time_raw="2026-05-03T11:00:00+08:00",
                status="地址异常",
                location="Shenzhen",
                source="seed",
                defaults={"event_time": timezone.now(), "raw_payload": {"seed": True}},
            )
            InventorySyncLog.objects.get_or_create(
                platform="tiktok",
                warehouse_id=empty_warehouse.code,
                defaults={"total_items": 0, "success_count": 0, "fail_count": 0, "message": "empty warehouse"},
            )
            InventoryAdjustment.objects.get_or_create(
                sku="SKU-DEMO-003",
                warehouse=empty_warehouse,
                defaults={"product": low_stock_product, "adjustment_type": "decrease", "quantity": 2, "reason": "低库存测试", "operator": "system"},
            )

        self.stdout.write(self.style.SUCCESS("seed_boundary_data completed"))
