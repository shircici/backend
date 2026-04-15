from __future__ import annotations

from decimal import Decimal

from django.apps import apps


def get_purchase_price_for_product(product_id: int) -> Decimal | None:
    """
    从 SKU 主数据取采购/供货成本：优先使用扩展字段 cost（若存在），否则以 price 的 85% 作为占位采购价。
    若商品下无任何 SKU，返回 None。
    """
    Sku = apps.get_model("sku_mgt", "Sku")
    sku = Sku.objects.filter(product_id=product_id, is_deleted=False).order_by("id").first()
    if not sku:
        return None
    if sku.cost is not None:
        return Decimal(str(sku.cost))
    return (Decimal(sku.price) * Decimal("0.85")).quantize(Decimal("0.01"))
