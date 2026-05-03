from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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
    help = "Seed realistic demo data for interface verification in MySQL."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Clear seeded rows before inserting")

    def handle(self, *args, **options):
        reset = bool(options["reset"])
        User = get_user_model()

        with transaction.atomic():
            if reset:
                LogisticsTrackingEvent.objects.all().delete()
                LogisticsShipment.objects.all().delete()
                OrderRemark.objects.all().delete()
                InventoryAdjustment.objects.all().delete()
                InventorySyncLog.objects.all().delete()
                CollectionTask.objects.all().delete()
                PlatformToken.objects.all().delete()
                LogisticsRateCard.objects.all().delete()
                Warehouse.objects.all().delete()
                Shop.objects.all().delete()
                Order.objects.all().delete()
                ProductVariant.objects.all().delete()
                Product.objects.all().delete()
                Sku.objects.all().delete()
                SkuProduct.objects.all().delete()
                Category.objects.all().delete()

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
            zero_stock_product, _ = Product.objects.get_or_create(
                platform="tiktok",
                platform_product_id="TT-DEMO-002",
                defaults={
                    "title": "零库存演示商品",
                    "images": ["https://example.com/demo-2.jpg"],
                    "attributes": {"color": "white"},
                    "price": Decimal("49.90"),
                    "stock": 0,
                },
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
                product=product,
                sku="AMZ-DEMO-001-RED",
                defaults={
                    "title": "跨境演示商品 - 红色",
                    "price": Decimal("31.90"),
                    "stock": 64,
                    "attributes": {"color": "red"},
                },
            )
            ProductVariant.objects.get_or_create(
                product=zero_stock_product,
                sku="TT-DEMO-002-WH",
                defaults={
                    "title": "零库存演示商品 - 白色",
                    "price": Decimal("52.90"),
                    "stock": 0,
                    "attributes": {"color": "white"},
                },
            )
            ProductVariant.objects.get_or_create(
                product=low_stock_product,
                sku="A-DEMO-003-BL",
                defaults={
                    "title": "低库存演示商品 - 蓝色",
                    "price": Decimal("21.90"),
                    "stock": 3,
                    "attributes": {"color": "blue"},
                },
            )
            Sku.objects.get_or_create(
                sku_code="SKU-DEMO-001",
                defaults={
                    "product_id": sku_product.id,
                    "product_name": sku_product.product_name,
                    "category_id": category.id,
                    "price": Decimal("29.90"),
                    "cost": Decimal("16.80"),
                    "stock": 128,
                    "status": 1,
                },
            )
            Sku.objects.get_or_create(
                sku_code="SKU-DEMO-002",
                defaults={
                    "product_id": sku_product.id,
                    "product_name": "跨境演示商品-备用款",
                    "category_id": category.id,
                    "price": Decimal("39.90"),
                    "cost": Decimal("20.80"),
                    "stock": 86,
                    "status": 1,
                },
            )
            Sku.objects.get_or_create(
                sku_code="SKU-DEMO-003",
                defaults={
                    "product_id": sku_product.id,
                    "product_name": "零库存演示商品",
                    "category_id": category.id,
                    "price": Decimal("49.90"),
                    "cost": Decimal("25.00"),
                    "stock": 0,
                    "status": 0,
                },
            )
            Sku.objects.get_or_create(
                sku_code="SKU-DEMO-004",
                defaults={
                    "product_id": sku_product.id,
                    "product_name": "低库存演示商品",
                    "category_id": category.id,
                    "price": Decimal("19.90"),
                    "cost": Decimal("8.90"),
                    "stock": 3,
                    "status": 1,
                },
            )

            warehouse, _ = Warehouse.objects.get_or_create(
                code="SZ-001",
                defaults={"name": "深圳前海仓", "address": {"country": "CN", "city": "深圳"}, "status": "active"},
            )
            Warehouse.objects.get_or_create(
                code="GZ-001",
                defaults={"name": "广州南沙仓", "address": {"country": "CN", "city": "广州"}, "status": "active"},
            )
            Warehouse.objects.get_or_create(
                code="EMPTY-001",
                defaults={"name": "空仓库", "address": {"country": "CN", "city": "东莞"}, "status": "active"},
            )
            Shop.objects.get_or_create(
                external_shop_id="shop-amz-001",
                defaults={"platform": "amazon", "name": "Amazon Demo Shop", "status": "active"},
            )
            Shop.objects.get_or_create(
                external_shop_id="shop-tt-001",
                defaults={"platform": "tiktok", "name": "TikTok Demo Shop", "status": "active"},
            )
            LogisticsRateCard.objects.get_or_create(
                carrier="YTO",
                destination_country="US",
                defaults={
                    "base_weight_kg": Decimal("0.50"),
                    "base_price": Decimal("48.00"),
                    "additional_price_per_kg": Decimal("18.00"),
                    "currency": "CNY",
                    "is_active": True,
                },
            )
            LogisticsRateCard.objects.get_or_create(
                carrier="SF",
                destination_country="JP",
                defaults={
                    "base_weight_kg": Decimal("0.50"),
                    "base_price": Decimal("36.00"),
                    "additional_price_per_kg": Decimal("15.00"),
                    "currency": "CNY",
                    "is_active": True,
                },
            )
            LogisticsRateCard.objects.get_or_create(
                carrier="JD",
                destination_country="CN",
                defaults={
                    "base_weight_kg": Decimal("0.50"),
                    "base_price": Decimal("12.00"),
                    "additional_price_per_kg": Decimal("6.00"),
                    "currency": "CNY",
                    "is_active": True,
                },
            )

            order1, _ = Order.objects.get_or_create(
                platform="amazon",
                order_no="AMZ202605030001",
                defaults={
                    "buyer_name": "Alice",
                    "status": Order.STATUS_PAID,
                    "amount": Decimal("59.80"),
                    "recipient_name": "Alice",
                    "recipient_phone": "13800000001",
                    "shipping_address": {"country": "US", "city": "Los Angeles"},
                },
            )
            order2, _ = Order.objects.get_or_create(
                platform="tiktok",
                order_no="TT202605030002",
                defaults={
                    "buyer_name": "Bob",
                    "status": Order.STATUS_SHIPPED,
                    "amount": Decimal("89.90"),
                    "recipient_name": "Bob",
                    "recipient_phone": "13800000002",
                    "shipping_address": {"country": "JP", "city": "Tokyo"},
                },
            )
            order3, _ = Order.objects.get_or_create(
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
            order4, _ = Order.objects.get_or_create(
                platform="amazon",
                order_no="AMZ202605030004",
                defaults={
                    "buyer_name": "Daisy",
                    "status": Order.STATUS_SIGNED,
                    "amount": Decimal("129.90"),
                    "recipient_name": "Daisy",
                    "recipient_phone": "13800000004",
                    "shipping_address": {"country": "US", "city": "New York"},
                },
            )

            shipment2, _ = LogisticsShipment.objects.get_or_create(
                order=order2,
                waybill_no="WB202605030002",
                defaults={"carrier": "SF", "status": LogisticsShipment.STATUS_IN_TRANSIT, "latest_event": "已出库"},
            )
            shipment1, _ = LogisticsShipment.objects.get_or_create(
                order=order1,
                waybill_no="WB202605030001",
                defaults={"carrier": "YTO", "status": LogisticsShipment.STATUS_DELIVERED, "latest_event": "已签收"},
            )
            LogisticsShipment.objects.get_or_create(
                order=order3,
                waybill_no="WB202605030003",
                defaults={"carrier": "JD", "status": LogisticsShipment.STATUS_EXCEPTION, "latest_event": "地址异常"},
            )
            LogisticsShipment.objects.get_or_create(
                order=order4,
                waybill_no="WB202605030004",
                defaults={"carrier": "YTO", "status": LogisticsShipment.STATUS_DELIVERED, "latest_event": "已签收"},
            )
            LogisticsTrackingEvent.objects.get_or_create(
                shipment=shipment1,
                event_time_raw="2026-05-03T09:00:00+08:00",
                status="已签收",
                location="Los Angeles",
                source="seed",
                defaults={"event_time": timezone.now(), "raw_payload": {"seed": True}},
            )
            LogisticsTrackingEvent.objects.get_or_create(
                shipment=shipment2,
                event_time_raw="2026-05-03T10:00:00+08:00",
                status="已出库",
                location="Shanghai",
                source="seed",
                defaults={"event_time": timezone.now(), "raw_payload": {"seed": True}},
            )
            LogisticsTrackingEvent.objects.get_or_create(
                shipment=shipment1,
                event_time_raw="2026-05-03T11:00:00+08:00",
                status="地址异常",
                location="Los Angeles",
                source="seed",
                defaults={"event_time": timezone.now(), "raw_payload": {"seed": True}},
            )
            InventorySyncLog.objects.get_or_create(
                platform="amazon",
                warehouse_id=warehouse.code,
                defaults={"total_items": 2, "success_count": 2, "fail_count": 0, "message": "seeded"},
            )
            InventorySyncLog.objects.get_or_create(
                platform="tiktok",
                warehouse_id="EMPTY-001",
                defaults={"total_items": 0, "success_count": 0, "fail_count": 0, "message": "empty warehouse"},
            )
            InventoryAdjustment.objects.get_or_create(
                sku="SKU-DEMO-001",
                warehouse=warehouse,
                defaults={
                    "product": SkuProduct.objects.first(),
                    "adjustment_type": "increase",
                    "quantity": 20,
                    "reason": "初始铺货",
                    "operator": "system",
                },
            )
            InventoryAdjustment.objects.get_or_create(
                sku="SKU-DEMO-003",
                warehouse=warehouse,
                defaults={
                    "product": SkuProduct.objects.first(),
                    "adjustment_type": "decrease",
                    "quantity": 5,
                    "reason": "低库存测试",
                    "operator": "system",
                },
            )
            OrderRemark.objects.get_or_create(
                order=order1,
                content="已确认收款，等待发货。",
                defaults={"operator": "system"},
            )
            CollectionTask.objects.get_or_create(
                platform="1688",
                status="success",
                defaults={"target_ids": ["123456789"], "result_message": "seeded"},
            )
            CollectionTask.objects.get_or_create(
                platform="amazon",
                status="running",
                defaults={"target_ids": ["AMZ-DEMO-001"], "result_message": "同步中"},
            )

            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(username="admin", password="Admin123456")

        self.stdout.write(self.style.SUCCESS("seed_interface_data completed"))
