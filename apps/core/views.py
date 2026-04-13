import uuid
import hashlib
import json
import csv

from django.conf import settings
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db import connections
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.common.rbac_permissions import HasApiIntegratorRole
from apps.common.responses import error_response, success_response

from .models import (
    ApiIdempotencyRecord,
    CollectionTask,
    DeadLetterTask,
    InventorySyncLog,
    LogisticsShipment,
    Order,
    PlatformToken,
    Product,
    ReplayAuditLog,
    Shop,
    SyncRule,
)
from .platform_clients import get_platform_client
from .permissions import IsOpsAdmin
from .serializers import (
    CollectionTaskCreateSerializer,
    CollectionTaskSerializer,
    InventorySyncLogSerializer,
    LogisticsShipmentSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
    ProductSerializer,
    ShopSerializer,
)
from .services import build_expire_time
from .tasks import execute_collection_task, refresh_platform_token, scheduled_inventory_sync


def _request_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


# RBAC：采集/同步/平台 Token 刷新等业务接口（Django Group + JWT）
_BUSINESS_API_PERMISSIONS = [IsAuthenticated, HasApiIntegratorRole]


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="获取平台授权 URL")
    def get(self, request, platform):
        try:
            client = get_platform_client(platform)
            state = request.query_params.get("state", str(uuid.uuid4()))
            login_url = client.get_oauth_authorize_url(state=state)
            return success_response({"authorization_url": login_url, "state": state})
        except Exception as exc:
            return error_response(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)


class AuthCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="平台 OAuth 回调并保存 Token")
    def get(self, request, platform):
        code = request.query_params.get("code")
        if not code:
            return error_response(message="code is required", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            client = get_platform_client(platform)
            token_payload = client.exchange_code_for_token(code)
            token_obj, _ = PlatformToken.objects.get_or_create(
                platform=platform,
                account_id=token_payload.get("account_id", "default"),
            )
            token_obj.set_tokens(token_payload["access_token"], token_payload["refresh_token"])
            token_obj.expires_at = build_expire_time(token_payload["expires_in"])
            token_obj.save()
            token_obj.cache_tokens()
            return success_response(
                {
                    "platform": token_obj.platform,
                    "account_id": token_obj.account_id,
                    "expires_at": token_obj.expires_at,
                }
            )
        except Exception as exc:
            return error_response(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)


class AuthRefreshView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="手动刷新平台 Token")
    def post(self, request, platform):
        account_id = request.data.get("account_id", "default")
        token_obj = get_object_or_404(PlatformToken, platform=platform, account_id=account_id)
        refresh_platform_token.delay(token_obj.id)
        return success_response({"queued": True, "token_id": token_obj.id})


class CollectionTaskCreateView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="创建采集任务并推送队列")
    def post(self, request):
        idem_key = request.headers.get("X-Idempotency-Key", "").strip()
        if idem_key:
            req_hash = _request_hash(request.data)
            existing = ApiIdempotencyRecord.objects.filter(idem_key=idem_key, endpoint=request.path).first()
            if existing and existing.request_hash == req_hash:
                return success_response(existing.response_data, status_code=existing.status_code)

        serializer = CollectionTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = CollectionTask.objects.create(
            platform=serializer.validated_data["platform"],
            target_ids=serializer.validated_data["target_ids"],
            status="pending",
        )
        execute_collection_task.delay(task.id)
        response_data = {"task_id": task.id, "status": task.status}
        if idem_key:
            ApiIdempotencyRecord.objects.update_or_create(
                idem_key=idem_key,
                endpoint=request.path,
                defaults={
                    "request_hash": _request_hash(request.data),
                    "response_data": response_data,
                    "status_code": status.HTTP_201_CREATED,
                },
            )
        return success_response(response_data, status_code=status.HTTP_201_CREATED)


class CollectionTaskStatusView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="查询采集任务状态")
    def get(self, request, task_id):
        task = get_object_or_404(CollectionTask, id=task_id)
        data = CollectionTaskSerializer(task).data
        return success_response(data)


class SyncTriggerView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="手动触发库存同步")
    def post(self, request):
        idem_key = request.headers.get("X-Idempotency-Key", "").strip()
        if idem_key:
            req_hash = _request_hash(request.data)
            existing = ApiIdempotencyRecord.objects.filter(idem_key=idem_key, endpoint=request.path).first()
            if existing and existing.request_hash == req_hash:
                return success_response(existing.response_data, status_code=existing.status_code)

        scheduled_inventory_sync.delay()
        response_data = {"queued": True}
        if idem_key:
            ApiIdempotencyRecord.objects.update_or_create(
                idem_key=idem_key,
                endpoint=request.path,
                defaults={"request_hash": _request_hash(request.data), "response_data": response_data, "status_code": 200},
            )
        return success_response(response_data)


class SyncLogView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="获取库存同步日志")
    def get(self, request):
        logs = InventorySyncLog.objects.all().order_by("-created_at")[:100]
        data = InventorySyncLogSerializer(logs, many=True).data
        return success_response(data)


class DeadLetterListView(APIView):
    permission_classes = [IsAuthenticated, IsOpsAdmin]

    @extend_schema(summary="查看 dead-letter 列表")
    def get(self, request):
        queryset = DeadLetterTask.objects.all().order_by("-created_at")
        status_value = request.query_params.get("status")
        task_name = request.query_params.get("task_name")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if task_name:
            queryset = queryset.filter(task_name=task_name)

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        page_size = min(max(page_size, 1), 200)
        paginator = Paginator(queryset, page_size)
        current_page = paginator.get_page(page)
        rows = current_page.object_list
        data = [
            {
                "id": row.id,
                "task_name": row.task_name,
                "payload": row.payload,
                "error_message": row.error_message,
                "retry_count": row.retry_count,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in rows
        ]
        return success_response(
            {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "page": current_page.number,
                "page_size": page_size,
                "results": data,
            }
        )


class DeadLetterReplayView(APIView):
    permission_classes = [IsAuthenticated, IsOpsAdmin]

    @extend_schema(summary="重放 dead-letter 任务")
    def post(self, request, dead_letter_id):
        row = get_object_or_404(DeadLetterTask, id=dead_letter_id)
        task_name = row.task_name
        payload = row.payload or {}
        operator = request.user.username if getattr(request, "user", None) and request.user.is_authenticated else "system"

        try:
            if task_name == "execute_collection_task":
                execute_collection_task.delay(payload["task_id"])
            elif task_name == "refresh_platform_token":
                refresh_platform_token.delay(payload["token_id"])
            elif task_name == "sync_inventory_by_rule":
                from .tasks import sync_inventory_by_rule

                sync_inventory_by_rule.delay(payload["sync_rule_id"])
            else:
                ReplayAuditLog.objects.create(
                    dead_letter_task=row,
                    operator=operator,
                    result="failed",
                    detail=f"Unsupported task_name: {task_name}",
                )
                return error_response(message=f"Unsupported task_name: {task_name}", status_code=400)

            row.status = DeadLetterTask.STATUS_REPLAYED
            row.retry_count += 1
            row.save(update_fields=["status", "retry_count", "updated_at"])
            ReplayAuditLog.objects.create(dead_letter_task=row, operator=operator, result="success", detail="replay queued")
            return success_response({"replayed": True, "dead_letter_id": row.id})
        except Exception as exc:
            ReplayAuditLog.objects.create(dead_letter_task=row, operator=operator, result="failed", detail=str(exc))
            return error_response(message=str(exc), status_code=500)


class ReplayAuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsOpsAdmin]

    @extend_schema(summary="查看重放审计日志")
    def get(self, request):
        queryset = ReplayAuditLog.objects.all().order_by("-created_at")
        dead_letter_id = request.query_params.get("dead_letter_id")
        if dead_letter_id:
            queryset = queryset.filter(dead_letter_task_id=dead_letter_id)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        page_size = min(max(page_size, 1), 200)
        paginator = Paginator(queryset, page_size)
        current_page = paginator.get_page(page)
        data = [
            {
                "id": row.id,
                "dead_letter_task_id": row.dead_letter_task_id,
                "operator": row.operator,
                "result": row.result,
                "detail": row.detail,
                "created_at": row.created_at,
            }
            for row in current_page.object_list
        ]
        return success_response(
            {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "page": current_page.number,
                "page_size": page_size,
                "results": data,
            }
        )


class OpsWhoAmIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="运维权限自检")
    def get(self, request):
        user = request.user
        ops_by_group = user.groups.filter(name="ops_admin").exists()
        ops_by_list = user.username in set(getattr(settings, "OPS_ADMIN_USERNAMES", []))
        is_ops_admin = user.is_superuser or ops_by_group or ops_by_list
        return success_response(
            {
                "username": user.username,
                "is_superuser": user.is_superuser,
                "ops_by_group": ops_by_group,
                "ops_by_list": ops_by_list,
                "is_ops_admin": is_ops_admin,
            }
        )


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(summary="系统健康检查")
    def get(self, request):
        checks = {"database": False, "cache": False}
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = True
        except Exception:
            checks["database"] = False

        try:
            cache.set("healthcheck:ping", "pong", timeout=10)
            checks["cache"] = cache.get("healthcheck:ping") == "pong"
        except Exception:
            checks["cache"] = False

        ok = all(checks.values())
        code = 200 if ok else 503
        return success_response(
            data={
                "status": "ok" if ok else "degraded",
                "checks": checks,
                "ops_admin_usernames": getattr(settings, "OPS_ADMIN_USERNAMES", []),
            },
            status_code=code,
            code=code,
            message="success" if ok else "service unavailable",
        )


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="获取当前用户信息")
    def get(self, request):
        user = request.user
        return success_response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
            }
        )


class GoodsListCreateView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="商品列表（分页/搜索）")
    def get(self, request):
        queryset = Product.objects.all().order_by("-updated_at")
        keyword = request.query_params.get("keyword", "").strip()
        platform = request.query_params.get("platform", "").strip()
        if keyword:
            queryset = queryset.filter(title__icontains=keyword)
        if platform:
            queryset = queryset.filter(platform=platform)

        page = int(request.query_params.get("page", 1))
        page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 200)
        paginator = Paginator(queryset, page_size)
        current_page = paginator.get_page(page)
        data = ProductSerializer(current_page.object_list, many=True).data
        return success_response(
            {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "page": current_page.number,
                "page_size": page_size,
                "results": data,
            }
        )

    @extend_schema(summary="创建商品")
    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return success_response(ProductSerializer(obj).data, status_code=201)


class GoodsDetailView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="商品详情")
    def get(self, request, goods_id):
        obj = get_object_or_404(Product, id=goods_id)
        return success_response(ProductSerializer(obj).data)

    @extend_schema(summary="更新商品")
    def put(self, request, goods_id):
        obj = get_object_or_404(Product, id=goods_id)
        serializer = ProductSerializer(instance=obj, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return success_response(ProductSerializer(obj).data)

    @extend_schema(summary="删除商品")
    def delete(self, request, goods_id):
        obj = get_object_or_404(Product, id=goods_id)
        obj.delete()
        return success_response({"deleted": True, "id": goods_id})


class ShopListView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="店铺列表")
    def get(self, request):
        shops = Shop.objects.all().order_by("-updated_at")[:200]
        return success_response(ShopSerializer(shops, many=True).data)


class InventoryAlertsView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="库存预警")
    def get(self, request):
        threshold = int(request.query_params.get("threshold", 10))
        queryset = Product.objects.filter(stock__lte=threshold).order_by("stock", "-updated_at")[:500]
        return success_response(
            {
                "threshold": threshold,
                "count": queryset.count(),
                "results": ProductSerializer(queryset, many=True).data,
            }
        )


class InventoryLogsView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="库存同步日志")
    def get(self, request):
        logs = InventorySyncLog.objects.all().order_by("-created_at")[:200]
        return success_response(InventorySyncLogSerializer(logs, many=True).data)


class InventorySyncView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="手动触发库存同步")
    def post(self, request):
        scheduled_inventory_sync.delay()
        return success_response({"queued": True})


class OrdersListView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="订单列表")
    def get(self, request):
        queryset = Order.objects.all().order_by("-created_at")
        status_value = request.query_params.get("status", "").strip()
        if status_value:
            queryset = queryset.filter(status=status_value)
        page = int(request.query_params.get("page", 1))
        page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 200)
        paginator = Paginator(queryset, page_size)
        current_page = paginator.get_page(page)
        data = OrderSerializer(current_page.object_list, many=True).data
        return success_response(
            {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "page": current_page.number,
                "page_size": page_size,
                "results": data,
            }
        )


class OrderStatusUpdateView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="更新订单状态")
    def put(self, request, order_id):
        obj = get_object_or_404(Order, id=order_id)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj.status = serializer.validated_data["status"]
        obj.save(update_fields=["status", "updated_at"])
        return success_response(OrderSerializer(obj).data)


class OrdersExportView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="导出订单")
    def get(self, request):
        queryset = Order.objects.all().order_by("-created_at")[:5000]
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="orders_export.csv"'
        writer = csv.writer(response)
        writer.writerow(["id", "platform", "order_no", "buyer_name", "status", "amount", "created_at"])
        for row in queryset:
            writer.writerow([row.id, row.platform, row.order_no, row.buyer_name, row.status, row.amount, row.created_at])
        return response


class LogisticsShipmentsView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="物流列表")
    def get(self, request):
        rows = LogisticsShipment.objects.select_related("order").all().order_by("-updated_at")[:500]
        return success_response(LogisticsShipmentSerializer(rows, many=True).data)


class LogisticsTrackView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="物流轨迹查询")
    def get(self, request, waybill):
        row = get_object_or_404(LogisticsShipment, waybill_no=waybill)
        data = {
            "waybill_no": row.waybill_no,
            "carrier": row.carrier,
            "status": row.status,
            "events": [
                {"time": row.updated_at, "desc": row.latest_event or "Shipment status updated"},
                {"time": row.created_at, "desc": "Shipment created"},
            ],
        }
        return success_response(data)
