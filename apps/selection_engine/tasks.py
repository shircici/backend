"""
选品引擎 Celery 任务：批量「商品 × 达人」ROAS 测算。

并发模型（推荐）：
    使用 ``group`` 为每个达人创建一个子任务，再用 ``chord`` 在全部完成后写收尾状态。
    这样 100 个达人对应 100 个独立任务，由多个 worker 并发执行。

备选（``chunks``）：
    若希望减少任务数量、每个任务顺序处理一小批达人，可使用::

        from celery import chord, group

        # 将参数列表按每块 10 条切开，每块一个子任务（子任务内需自行 for 循环）
        args_list = [(product_id, inf_id, batch_id, min_roas, ideal_roas) for inf_id in influencer_ids]
        header = group(
            calculate_influencer_chunk.s(chunk)
            for chunk in [args_list[i : i + 10] for i in range(0, len(args_list), 10)]
        )
        chord(header)(finalize_influencer_batch.s(batch_id))

    其中 ``calculate_influencer_chunk`` 需自行实现为接收 ``list[tuple]`` 并循环调用本模块中的单条计算逻辑。
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Iterable, List, Sequence
from uuid import uuid4

from celery import chord, group, shared_task

from .calculation import calculate_roas
from .exceptions import RoasCalculationError
from .models import InfluencerMatchPreview
from .redis_progress import (
    finalize_batch_status,
    increment_batch_progress,
    init_batch_progress,
    mark_batch_empty_done,
)

logger = logging.getLogger(__name__)


def _grade_for_roas(roas: Decimal, *, min_roas: Decimal, ideal_roas: Decimal) -> str:
    if roas >= ideal_roas:
        return "A"
    if roas >= min_roas:
        return "B"
    return "C"


def _stub_match_inputs(product_id: int, influencer_id: str) -> dict[str, Decimal]:
    """
    占位：用达人 ID 生成可重复的模拟收入与成本。
    接入真实数据后，可改为读取达人报价、预估 GMV、WMS 成本等。
    """
    h = abs(hash(influencer_id))
    revenue = Decimal("8000") + Decimal(h % 5000)
    promotion = Decimal(h % 200 + 1)
    fixed = Decimal("300") + Decimal(product_id % 100)
    variable = Decimal(h % 150 + 50)
    return {
        "estimated_revenue": revenue,
        "promotion_cost": promotion,
        "fixed_cost": fixed,
        "variable_cost": variable,
    }


@shared_task(
    name="apps.selection_engine.tasks.calculate_single_influencer_roas",
    bind=True,
    max_retries=0,
    ignore_result=False,
)
def calculate_single_influencer_roas(
    self,
    product_id: int,
    influencer_id: str,
    batch_id: str,
    min_roas: float | str = 3,
    ideal_roas: float | str = 5,
) -> dict[str, Any]:
    """
    单个达人一条子任务：计算 ROAS → 定级 A/B/C → 写入预览表 → 更新 Redis 进度。
    """
    failed = False
    detail: dict[str, Any] = {"product_id": product_id, "influencer_id": influencer_id}
    roas_val: Decimal | None = None
    grade = "C"

    try:
        inputs = _stub_match_inputs(product_id, influencer_id)
        detail["inputs"] = {k: str(v) for k, v in inputs.items()}
        roas_val = calculate_roas(
            inputs["estimated_revenue"],
            inputs["promotion_cost"],
            inputs["fixed_cost"],
            inputs["variable_cost"],
        )
        min_d = Decimal(str(min_roas))
        ideal_d = Decimal(str(ideal_roas))
        grade = _grade_for_roas(roas_val, min_roas=min_d, ideal_roas=ideal_d)
    except RoasCalculationError as exc:
        failed = True
        detail["error"] = str(exc)
        grade = "C"
    except Exception as exc:  # noqa: BLE001 — 子任务需吞掉异常以免 chord 中断
        logger.exception("calculate_single_influencer_roas failed batch=%s inf=%s", batch_id, influencer_id)
        failed = True
        detail["error"] = str(exc)
        grade = "C"

    InfluencerMatchPreview.objects.update_or_create(
        batch_id=batch_id,
        influencer_id=influencer_id,
        defaults={
            "product_id": product_id,
            "roas": roas_val,
            "grade": grade,
            "detail": detail,
        },
    )

    increment_batch_progress(batch_id, failed=failed)
    return {
        "batch_id": batch_id,
        "influencer_id": influencer_id,
        "grade": grade,
        "roas": str(roas_val) if roas_val is not None else None,
        "failed": failed,
    }


@shared_task(name="apps.selection_engine.tasks.finalize_influencer_batch", ignore_result=True)
def finalize_influencer_batch(results: List[Any] | None, batch_id: str) -> None:
    """
    chord 回调：全部子任务结束后兜底更新 Redis 状态（子任务内已按条递增 done）。
    ``results`` 为各子任务返回值列表；失败子任务若未吞异常则可能为 Exception 占位，此处仅打日志。
    """
    if results:
        for item in results:
            if isinstance(item, Exception):
                logger.warning("子任务异常 batch_id=%s err=%s", batch_id, item)
    finalize_batch_status(batch_id)


def _normalize_influencer_ids(influencer_id_list: Sequence[Any]) -> List[str]:
    out: List[str] = []
    for x in influencer_id_list:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


@shared_task(name="apps.selection_engine.tasks.batch_calculate_influencer_roas", ignore_result=False)
def batch_calculate_influencer_roas(
    product_id: int,
    influencer_id_list: Iterable[Any],
    batch_id: str | None = None,
    min_roas: float | str = 3,
    ideal_roas: float | str = 5,
) -> str:
    """
    编排入口：接收 ``product_id`` 与 ``influencer_id_list``，初始化 Redis 进度，
    使用 ``group + chord`` 并发调度单达人任务，返回 ``batch_id`` 供前端轮询进度与预览数据。

    注意：需配置路由到 ``selection`` 队列并由消费该队列的 worker 执行（见 settings 示例）。
    """
    bid = batch_id or str(uuid4())
    ids = _normalize_influencer_ids(list(influencer_id_list))

    if not ids:
        mark_batch_empty_done(bid)
        finalize_influencer_batch.delay([], bid)
        return bid

    init_batch_progress(bid, len(ids))

    header = group(
        calculate_single_influencer_roas.s(product_id, inf_id, bid, min_roas, ideal_roas) for inf_id in ids
    )
    chord(header)(finalize_influencer_batch.s(bid)).apply_async()
    logger.info("batch_calculate_influencer_roas dispatched batch_id=%s total=%s", bid, len(ids))
    return bid
