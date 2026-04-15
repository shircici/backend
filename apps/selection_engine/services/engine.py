from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..calculation import calculate_roas
from ..exceptions import RoasCalculationError
from .algorithm_config import get_active_thresholds
from .decision import decision_label_for_roas
from .product_sources import get_purchase_price_for_product
from .wms import WmsFreightError, fetch_freight_for_product


class SelectionProductNotFound(Exception):
    """SKU 主数据中找不到该商品下的有效 SKU。"""


def compute_selection_roas(
    *,
    product_id: int,
    promotion_cost: Decimal,
    estimated_revenue: Decimal,
    commission_rate: Decimal,
) -> tuple[Decimal, str, dict[str, Any]]:
    """
    汇总：采购价（DB）+ 运费（WMS）+ 平台佣金（按预估收入比例）+ 宣传费用 -> ROAS 与决策标签。
    固定成本 = 采购价；变量成本 = 运费 + 预估收入 * 佣金率。
    """
    purchase = get_purchase_price_for_product(product_id)
    if purchase is None:
        raise SelectionProductNotFound()

    try:
        freight = fetch_freight_for_product(product_id)
    except WmsFreightError as exc:
        raise WmsFreightError(str(exc)) from exc

    fixed_cost = purchase
    variable_cost = (freight + estimated_revenue * commission_rate).quantize(Decimal("0.000001"))

    roas = calculate_roas(estimated_revenue, promotion_cost, fixed_cost, variable_cost)
    min_roas, ideal_roas = get_active_thresholds()
    label = decision_label_for_roas(roas, min_roas=min_roas, ideal_roas=ideal_roas)

    breakdown = {
        "purchase_price": str(purchase),
        "freight": str(freight),
        "commission_rate": str(commission_rate),
        "commission_amount": str((estimated_revenue * commission_rate).quantize(Decimal("0.000001"))),
        "fixed_cost": str(fixed_cost),
        "variable_cost": str(variable_cost),
        "promotion_cost": str(promotion_cost),
        "estimated_revenue": str(estimated_revenue),
        "min_roas": str(min_roas),
        "ideal_roas": str(ideal_roas),
    }
    return roas, label, breakdown
