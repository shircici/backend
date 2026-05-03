from django.test import TestCase
from rest_framework.test import APIClient

from apps.sku_mgt.models import Category, Product, Sku


class SkuApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="测试分类", parent_id=0)
        self.product = Product.objects.create(
            product_code="P-1001",
            product_name="测试商品",
            category=self.category,
        )
        self.sku = Sku.objects.create(
            sku_code="SKU-1001",
            product_id=self.product.id,
            product_name="测试商品",
            category_id=self.category.id,
            price="19.90",
            cost="9.90",
            stock=12,
            status=1,
        )

    def test_sku_detail_returns_real_data(self):
        resp = self.client.get(f"/api/sku/detail/{self.sku.sku_code}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertEqual(resp.data["data"]["sku_code"], self.sku.sku_code)

    def test_sku_list_returns_created_sku(self):
        resp = self.client.get("/api/sku/list/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertTrue(any(item["sku_code"] == self.sku.sku_code for item in resp.data["data"] if isinstance(resp.data["data"], list)))

    def test_sku_search_requires_keyword(self):
        resp = self.client.get("/api/sku/search/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], 400)
