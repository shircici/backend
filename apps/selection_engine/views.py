from __future__ import annotations

import logging
from decimal import Decimal
import json
import time

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.views import APIView

from apps.common.responses import error_response, success_response

from .errors import PRODUCT_NOT_FOUND, ROAS_DENOMINATOR_ZERO, ROAS_INVALID_INPUT, WMS_FREIGHT_FAILED
from .exceptions import RoasCalculationError
from .models import DecisionLog, InfluencerMatchPreview
from .pagination import InfluencerPreviewPagination
from .permissions import CanAccessSelectionEngine
from .redis_progress import get_batch_progress
from .serializers import (
    InfluencerBatchSerializer,
    InfluencerMatchPreviewSerializer,
    SelectionCalculateSerializer,
)
from .services.algorithm_config import get_active_thresholds
from .services.engine import SelectionProductNotFound, compute_selection_roas
from .services.wms import WmsFreightError
from .tasks import batch_calculate_influencer_roas

logger = logging.getLogger(__name__)


def _agent_log(hypothesis_id: str, message: str, data: dict) -> None:
    # region agent log
    try:
        with open("debug-12656f.log", "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "12656f",
                        "runId": "pre-fix",
                        "hypothesisId": hypothesis_id,
                        "location": "apps/selection_engine/views.py:CalculateView.post",
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass
    # endregion


def _default_commission_rate() -> Decimal:
    raw = getattr(settings, "SELECTION_DEFAULT_COMMISSION_RATE", "0.08")
    return Decimal(str(raw))


class CalculateView(APIView):
    """
    单次选品测算：采购价（SKU）+ 运费（WMS）+ 佣金 + 宣传费 -> ROAS + 决策标签，并写入 DecisionLog。
    """

    permission_classes = [CanAccessSelectionEngine]

    @extend_schema(
        request=SelectionCalculateSerializer,
        responses={
            200: OpenApiResponse(description="测算成功"),
            400: OpenApiResponse(description="参数或 ROAS 不可计算"),
            403: OpenApiResponse(description="无 RBAC 权限"),
            404: OpenApiResponse(description="商品无 SKU"),
            502: OpenApiResponse(description="WMS 运费失败"),
        },
    )
    def post(self, request, *args, **kwargs):
        ser = SelectionCalculateSerializer(data=request.data)
        if not ser.is_valid():
            return error_response(
                message="参数校验失败",
                code=400,
                data={"error_code": ROAS_INVALID_INPUT, "fields": ser.errors},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        product_id = ser.validated_data["product_id"]
        promotion_cost = ser.validated_data["promotion_cost"]
        estimated_revenue = ser.validated_data["estimated_revenue"]
        _agent_log(
            "H3_H4",
            "calculate request validated",
            {
                "path": request.path,
                "product_id": product_id,
                "promotion_cost": str(promotion_cost),
                "estimated_revenue": str(estimated_revenue),
            },
        )
        commission_rate = ser.validated_data.get("commission_rate")
        if commission_rate is None:
            commission_rate = _default_commission_rate()

        try:
            roas, label, breakdown = compute_selection_roas(
                product_id=product_id,
                promotion_cost=promotion_cost,
                estimated_revenue=estimated_revenue,
                commission_rate=commission_rate,
            )
        except SelectionProductNotFound:
            return error_response(
                message="未找到该商品下的有效 SKU，无法取采购价",
                code=404,
                data={"error_code": PRODUCT_NOT_FOUND},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except WmsFreightError as exc:
            logger.warning("WMS freight error product_id=%s err=%s", product_id, exc)
            _agent_log(
                "H1_H2_H4",
                "caught WmsFreightError and returning 502",
                {"product_id": product_id, "error": str(exc)},
            )
            return error_response(
                message="获取实时运费失败，请稍后重试",
                code=502,
                data={"error_code": WMS_FREIGHT_FAILED},
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except RoasCalculationError as exc:
            return error_response(
                message=str(exc),
                code=400,
                data={"error_code": ROAS_DENOMINATOR_ZERO},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                code=400,
                data={"error_code": ROAS_INVALID_INPUT},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        _agent_log(
            "H5",
            "calculate succeeded",
            {"product_id": product_id, "roas": str(roas), "label": label},
        )

        input_params = {
            **{k: ser.validated_data[k] for k in ("product_id", "promotion_cost", "estimated_revenue")},
            "commission_rate": str(commission_rate),
            "breakdown": breakdown,
        }
        DecisionLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            product_id=product_id,
            input_params=input_params,
            roas=roas,
            decision_label=label,
        )

        return success_response(
            data={
                "roas": str(roas),
                "decision_label": label,
                "breakdown": breakdown,
            },
            message="ok",
            code=200,
            status_code=status.HTTP_200_OK,
        )


class DemoDecisionCalculateView(CalculateView):
    """兼容旧路径：/api/v1/decision/calculate/ 直接复用真实测算实现。"""

    @extend_schema(summary="选品决策计算（兼容旧路径，真实生产实现）")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class InfluencerBatchCalculateView(APIView):
    """一键批量测算达人：Celery 异步；HTTP 仅等待编排任务返回 batch_id（通常极短）。"""

    permission_classes = [CanAccessSelectionEngine]

    @extend_schema(
        request=InfluencerBatchSerializer,
        responses={200: OpenApiResponse(description="已受理"), 400: OpenApiResponse(description="参数错误")},
    )
    def post(self, request, *args, **kwargs):
        ser = InfluencerBatchSerializer(data=request.data)
        if not ser.is_valid():
            return error_response(
                message="参数校验失败",
                code=400,
                data={"error_code": ROAS_INVALID_INPUT, "fields": ser.errors},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        product_id = ser.validated_data["product_id"]
        influencer_ids = ser.validated_data["influencer_ids"]

        min_roas, ideal_roas = get_active_thresholds()
        async_res = batch_calculate_influencer_roas.delay(
            product_id,
            influencer_ids,
            None,
            float(min_roas),
            float(ideal_roas),
        )
        bid = async_res.get(timeout=60)

        return success_response(
            data={
                "batch_id": bid,
                "celery_parent_task_id": async_res.id,
                "websocket_url_template": "/ws/selection/batch/{batch_id}/?token=<JWT access>",
                "poll_hint": "轮询 GET /api/selection/batch/<batch_id>/progress/ 与 .../preview/；"
                "或使用 WebSocket 订阅实时进度（需 ASGI + daphne/uvicorn）",
            },
            message="accepted",
            code=200,
            status_code=status.HTTP_200_OK,
        )


class BatchProgressView(APIView):
    """批量测算进度（Redis），供前端轮询；WebSocket 可在网关侧订阅同源数据。"""

    permission_classes = [CanAccessSelectionEngine]

    @extend_schema(responses={200: OpenApiResponse(description="进度字典")})
    def get(self, request, batch_id: str, *args, **kwargs):
        prog = get_batch_progress(batch_id)
        if not prog:
            return error_response(
                message="未找到该批次或已过期",
                code=404,
                data={"error_code": "BATCH_NOT_FOUND"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=prog, message="ok", code=200, status_code=status.HTTP_200_OK)


class BatchPreviewListView(APIView):
    """批量测算结果预览（建议等级 A/B/C），limit/offset 分页。"""

    permission_classes = [CanAccessSelectionEngine]

    @extend_schema(responses={200: OpenApiResponse(description="分页列表")})
    def get(self, request, batch_id: str, *args, **kwargs):
        qs = InfluencerMatchPreview.objects.filter(batch_id=batch_id).order_by("-roas", "id")
        paginator = InfluencerPreviewPagination()
        page = paginator.paginate_queryset(qs, request)
        ser = InfluencerMatchPreviewSerializer(page, many=True)
        total = qs.count()
        payload = {
            "count": total,
            "results": ser.data,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        }
        return success_response(data=payload, message="ok", code=200, status_code=status.HTTP_200_OK)
