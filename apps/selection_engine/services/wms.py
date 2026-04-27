from __future__ import annotations

import logging
import os
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


class WmsFreightError(Exception):
    """WMS 运费接口不可用或返回非法数据。"""


def fetch_freight_for_product(product_id: int) -> Decimal:
    """
    联动 WMS 获取实时运费（元）。
    当前为可配置占位：环境变量 WMS_MOCK_FREIGHT 为基础运费，按 product_id 做小幅抖动便于联调。
    接入真实 WMS 时在此发起 HTTP/gRPC 调用并解析金额。
    """
    # region agent log
    try:
        with open("debug-12656f.log", "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "12656f",
                        "runId": "pre-fix",
                        "hypothesisId": "H1_H2",
                        "location": "apps/selection_engine/services/wms.py:fetch_freight_for_product",
                        "message": "enter fetch_freight_for_product",
                        "data": {"product_id": product_id, "env_has_value": bool(os.getenv("WMS_MOCK_FREIGHT"))},
                        "timestamp": int(__import__("time").time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion
    try:
        base = Decimal(os.getenv("WMS_MOCK_FREIGHT", "12.50"))
    except Exception as exc:  # noqa: BLE001
        # region agent log
        try:
            with open("debug-12656f.log", "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "12656f",
                            "runId": "pre-fix",
                            "hypothesisId": "H1",
                            "location": "apps/selection_engine/services/wms.py:fetch_freight_for_product",
                            "message": "WMS_MOCK_FREIGHT invalid decimal",
                            "data": {"raw_value": os.getenv("WMS_MOCK_FREIGHT", "12.50")},
                            "timestamp": int(__import__("time").time() * 1000),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:
            pass
        # endregion
        logger.exception("WMS_MOCK_FREIGHT 非法")
        raise WmsFreightError("运费配置非法") from exc
    jitter = Decimal(product_id % 7) * Decimal("0.5")
    result = (base + jitter).quantize(Decimal("0.01"))
    # region agent log
    try:
        with open("debug-12656f.log", "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "12656f",
                        "runId": "pre-fix",
                        "hypothesisId": "H2",
                        "location": "apps/selection_engine/services/wms.py:fetch_freight_for_product",
                        "message": "computed freight",
                        "data": {"base": str(base), "jitter": str(jitter), "result": str(result)},
                        "timestamp": int(__import__("time").time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion
    return result
