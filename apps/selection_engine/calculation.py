from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Union

from .exceptions import RoasCalculationError

Number = Union[Decimal, int, float, str]


def _to_decimal(value: Number, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 无法转换为 Decimal：{value!r}") from exc


def calculate_roas(
    estimated_revenue: Number,
    promotion_cost: Number,
    fixed_cost: Number,
    variable_cost: Number,
) -> Decimal:
    """
    计算广告投资回报率（ROAS）。

    ROAS = 预估收入 / (宣传费用 + 固定成本 + 变量成本)

    使用 Decimal 保证金额与比例精度；当分母为 0 时抛出 RoasCalculationError。
    说明：仅宣传费用为 0 时，只要固定成本与变量成本之和不为 0，分母仍非 0；
    当三项成本之和为 0 时无法计算 ROAS，按异常处理。
    """
    revenue = _to_decimal(estimated_revenue, field_name="estimated_revenue")
    promo = _to_decimal(promotion_cost, field_name="promotion_cost")
    fixed = _to_decimal(fixed_cost, field_name="fixed_cost")
    variable = _to_decimal(variable_cost, field_name="variable_cost")

    denominator = promo + fixed + variable
    if denominator == 0:
        raise RoasCalculationError("总成本为 0（宣传费用 + 固定成本 + 变量成本），无法计算 ROAS")

    return (revenue / denominator).quantize(Decimal("0.000001"))
