from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import LogisticsShipment, Order, OrderRemark, PlatformToken, Product, Shop, Warehouse
from apps.sku_mgt.models import Category, Product as SkuProduct, Sku


class CoreApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username="tester", password="Pass123456")
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name="测试分类", parent_id=0)
        self.sku_product = SkuProduct.objects.create(
            product_code="P-2001",
            product_name="核心测试商品",
            category=self.category,
        )
        self.product = Product.objects.create(
            platform="amazon",
            platform_product_id="AMZ-2001",
            title="核心测试商品",
            price="29.90",
            stock=20,
        )
        self.zero_stock_product = Product.objects.create(
            platform="tiktok",
            platform_product_id="TT-2001",
            title="低库存测试商品",
            price="19.90",
            stock=0,
        )
        self.order = Order.objects.create(
            platform="amazon",
            order_no="AMZ-ORDER-2001",
            buyer_name="Buyer",
            status=Order.STATUS_PENDING,
            amount="29.90",
            recipient_name="Receiver",
            recipient_phone="13800000000",
            shipping_address={"city": "Shenzhen"},
        )
        self.shipped_order = Order.objects.create(
            platform="tiktok",
            order_no="TT-ORDER-2002",
            buyer_name="Buyer2",
            status=Order.STATUS_SHIPPED,
            amount="49.90",
            recipient_name="Receiver2",
            recipient_phone="13800000001",
            shipping_address={"city": "Shanghai"},
        )
        self.warehouse = Warehouse.objects.create(
            name="深圳仓",
            code="SZ-TEST",
            address={"city": "Shenzhen"},
        )
        self.shop = Shop.objects.create(
            platform="amazon",
            external_shop_id="shop-2001",
            name="Amazon Test Shop",
        )
        PlatformToken.objects.create(
            platform="amazon",
            account_id="default",
            access_token_encrypted="enc-access",
            refresh_token_encrypted="enc-refresh",
            expires_at="2030-01-01T00:00:00Z",
        )

    def test_ai_chat_uses_production_structure(self):
        resp = self.client.post("/api/ai/chat/", {"action": "chat", "content": "hello"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertEqual(resp.data["data"]["action"], "chat")
        self.assertEqual(resp.data["data"]["usage"]["mode"], "production")

    def test_ai_translate_uses_production_structure(self):
        resp = self.client.post(
            "/api/ai/translate/",
            {"action": "translate", "content": "你好", "target_language": "en"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["target_language"], "en")
        self.assertIn("Translated", resp.data["data"]["result"])

    def test_ai_image_generate_uses_production_structure(self):
        resp = self.client.post(
            "/api/ai/image/generate/",
            {"action": "image_generate", "content": "product banner"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["job_status"], "queued")

    def test_inventory_low_stock_boundary(self):
        resp = self.client.get("/api/inventory/overview?threshold=5")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["data"]["out_of_stock_count"], 1)

    def test_inventory_adjust_increase_and_decrease(self):
        increase = self.client.post(
            "/api/inventory/adjust",
            {
                "sku": self.product.platform_product_id,
                "warehouse_code": self.warehouse.code,
                "adjustment_type": "increase",
                "quantity": 5,
                "reason": "补货",
            },
            format="json",
        )
        self.assertEqual(increase.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 25)

        decrease = self.client.post(
            "/api/inventory/adjust",
            {
                "sku": self.product.platform_product_id,
                "warehouse_code": self.warehouse.code,
                "adjustment_type": "decrease",
                "quantity": 3,
                "reason": "出库",
            },
            format="json",
        )
        self.assertEqual(decrease.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 22)

    def test_dashboard_new_orders_since(self):
        resp = self.client.get("/api/dashboard/new-orders-since")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertIn("new_orders", resp.data["data"])

    def test_order_remark_create_and_list(self):
        post_resp = self.client.post(
            f"/api/orders/{self.order.id}/remark/",
            {"content": "已联系客户确认地址"},
            format="json",
        )
        self.assertEqual(post_resp.status_code, 200)
        self.assertEqual(post_resp.data["code"], 200)
        self.assertEqual(OrderRemark.objects.filter(order=self.order).count(), 1)

        get_resp = self.client.get(f"/api/orders/{self.order.id}/remark/")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.data["code"], 200)
        self.assertGreaterEqual(get_resp.data["data"]["count"], 1)

    def test_order_confirm_and_ship_flow(self):
        confirm_resp = self.client.post(f"/api/orders/{self.order.id}/confirm/", format="json")
        self.assertEqual(confirm_resp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)

        ship_resp = self.client.post(
            f"/api/orders/{self.order.id}/ship/",
            {"waybill_no": "WB-2001", "carrier": "SF"},
            format="json",
        )
        self.assertEqual(ship_resp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_SHIPPED)

    def test_inventory_overview_returns_counts(self):
        resp = self.client.get("/api/inventory/overview")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertIn("total_sku", resp.data["data"])

    def test_goods_list_returns_real_product(self):
        resp = self.client.get("/api/goods/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertTrue(any(item["id"] == self.product.id for item in resp.data["data"]["results"]))

    def test_goods_search_by_platform_and_zero_stock(self):
        resp = self.client.get("/api/goods/?platform=tiktok")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any(item["id"] == self.zero_stock_product.id for item in resp.data["data"]["results"]))

    def test_order_status_can_move_to_cancelled(self):
        resp = self.client.put(
            f"/api/orders/{self.order.id}/status",
            {"status": Order.STATUS_CANCELLED},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)

    def test_logistics_shipments_and_exception_data_available(self):
        shipment = LogisticsShipment.objects.create(
            order=self.shipped_order,
            waybill_no="WB-2002",
            carrier="JD",
            status=LogisticsShipment.STATUS_EXCEPTION,
            latest_event="地址异常",
        )
        self.assertEqual(shipment.status, LogisticsShipment.STATUS_EXCEPTION)

    def test_logistics_carriers_and_sync_flow(self):
        resp = self.client.get("/api/logistics/carriers/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("carriers", resp.data["data"])

        sync_resp = self.client.post("/api/logistics/sync/", {"waybill_no": "WB-2001"}, format="json")
        self.assertEqual(sync_resp.status_code, 200)
        self.assertIn("status", sync_resp.data["data"])

    def test_shop_unbind_updates_status_and_clears_tokens(self):
        resp = self.client.post("/api/shops/unbind/", {"shop_id": self.shop.id}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, "unbound")
        self.assertFalse(PlatformToken.objects.filter(platform=self.shop.platform).exists())

    def test_image_upload_rejects_missing_file(self):
        resp = self.client.post("/api/v1/upload/image/", {}, format="multipart")
        self.assertEqual(resp.status_code, 400)
