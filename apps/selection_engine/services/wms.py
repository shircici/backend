from __future__ import annotations

import logging
import os
from decimal import Decimal

logger = logging.getLogger(__name__)


class WmsFreightError(Exception):
    """WMS 运费接口不可用或返回非法数据。"""


def fetch_freight_for_product(product_id: int) -> Decimal:
    """
    联动 WMS 获取实时运费（元）。
    当前为可配置占位：环境变量 WMS_MOCK_FREIGHT 为基础运费，按 product_id 做小幅抖动便于联调。
    接入真实 WMS 时在此发起 HTTP/gRPC 调用并解析金额。
    """
    try:
        base = Decimal(os.getenv("WMS_MOCK_FREIGHT", "12.50"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("WMS_MOCK_FREIGHT 非法")
        raise WmsFreightError("运费配置非法") from exc
    jitter = Decimal(product_id % 7) * Decimal("0.5")
    return (base + jitter).quantize(Decimal("0.01"))
