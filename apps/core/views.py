import uuid
import hashlib
import json
import csv
import time
from datetime import timedelta
from django.conf import settings
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db import connections
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.rbac_permissions import HasApiIntegratorRole
from apps.common.responses import error_response, success_response

from .models import (
    ApiIdempotencyRecord,
    CollectionTask,
    DeadLetterTask,
    InventorySyncLog,
    LogisticsRateCard,
    LogisticsShipment,
    LogisticsTrackingEvent,
    Order,
    PlatformToken,
    UserPhoneBinding,
    AccountDeletionLog,
    SmsDispatchLog,
    PhoneRebindAppeal,
    DevicePhoneRelation,
    Product,
    ReplayAuditLog,
    Shop,
    SyncRule,
)
from .platform_clients import get_platform_client
from .logistics_clients import get_logistics_aggregator_client
from .permissions import HasOrderEditPermission, IsOpsAdmin
from .serializers import (
    CollectionTaskCreateSerializer,
    CollectionTaskSerializer,
    InventorySyncLogSerializer,
    FreightEstimateQuerySerializer,
    LogisticsShipmentSerializer,
    LogisticsRateCardSerializer,
    OrderSerializer,
    OrderAddressUpdateSerializer,
    OrderStatusUpdateSerializer,
    ProductSerializer,
    SmsCodeSendSerializer,
    SmsCodeVerifySerializer,
    MobileAuthSerializer,
    AccountDeleteSerializer,
    PhoneRebindAppealSerializer,
    SmsChannelStatsQuerySerializer,
    ShopSerializer,
)
from .sms_providers import SmsSendError
from .sms_service import (
    check_send_rate_limits,
    create_captcha_challenge,
    generate_sms_code,
    get_client_ip,
    check_and_incr_global_sms_limit,
    is_device_blacklisted,
    register_device_phone_attempt,
    record_send_success,
    store_sms_code,
    verify_sms_code_with_lua,
    validate_captcha_if_required,
)
from .services import build_expire_time
from .tasks import execute_collection_task, refresh_platform_token, scheduled_inventory_sync, send_sms_with_failover


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


class CaptchaChallengeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="获取图形验证码（人机挑战）")
    def get(self, request):
        return success_response(data=create_captcha_challenge())


class SmsCodeSendView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="发送短信验证码")
    def post(self, request):
        serializer = SmsCodeSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        country_code = serializer.validated_data.get("country_code", "86")
        full_phone = f"+{country_code}{phone}"
        voice = serializer.validated_data.get("voice", False)
        captcha_err = validate_captcha_if_required(
            serializer.validated_data.get("captcha_id") or None,
            serializer.validated_data.get("captcha_answer"),
        )
        if captcha_err:
            return error_response(message=captcha_err, status_code=400)

        global_limit_err = check_and_incr_global_sms_limit()
        if global_limit_err:
            return error_response(message=global_limit_err, status_code=429, code=429)

        client_ip = get_client_ip(request.META)
        limit_err = check_send_rate_limits(full_phone, client_ip)
        if limit_err:
            return error_response(
                message=limit_err,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                code=429,
            )

        code = generate_sms_code()
        message_type = "voice" if voice else "sms"
        try:
            send_result = send_sms_with_failover.delay(phone=full_phone, code=code, message_type=message_type).get(timeout=15)
        except SmsSendError as exc:
            return error_response(message=str(exc), status_code=400)
        except Exception as exc:
            return error_response(message=f"sms dispatch failed: {exc}", status_code=400)

        store_sms_code(full_phone, code)
        record_send_success(full_phone, client_ip)
        ttl = int(getattr(settings, "SMS_CODE_TTL_SECONDS", 300))
        return success_response(
            {
                "phone": full_phone,
                "expires_in": ttl,
                "provider": send_result.get("provider"),
                "biz_id": send_result.get("biz_id"),
                "message_type": message_type,
                "code": code if settings.DEBUG else None,
            }
        )


class SmsCodeVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="校验短信验证码")
    def post(self, request):
        serializer = SmsCodeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        ok, err_msg, status_code = verify_sms_code_with_lua(phone, code)
        if not ok:
            return error_response(message=err_msg or "error", status_code=status_code, code=status_code)
        return success_response({"verified": True, "phone": phone})


def _mask_mobile(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 7:
        return phone
    return f"{digits[:3]}****{digits[-4:]}"


class MobileAuthLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="手机号验证码登录/注册（合并）")
    def post(self, request):
        serializer = MobileAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["agreed_privacy"]:
            return error_response(message="必须同意隐私协议", status_code=400)

        country_code = serializer.validated_data["country_code"]
        mobile = serializer.validated_data["mobile"]
        full_phone = f"+{country_code}{mobile}"
        device_id = request.headers.get("X-Device-ID", "").strip()
        if device_id and is_device_blacklisted(device_id):
            return error_response(message="设备已被风控拦截", status_code=403, code=403)

        ok, err_msg, status_code = verify_sms_code_with_lua(full_phone, serializer.validated_data["code"])
        if not ok:
            return error_response(message=err_msg or "error", status_code=status_code, code=status_code)

        User = get_user_model()
        with transaction.atomic():
            binding = UserPhoneBinding.objects.select_for_update().filter(
                country_code=country_code,
                phone_number=mobile,
            ).first()
            created = False
            if binding:
                user = binding.user
            else:
                ts = int(time.time())
                username = f"u_{country_code}_{mobile}_{ts}"
                user = User.objects.create_user(username=username)
                UserPhoneBinding.objects.create(user=user, country_code=country_code, phone_number=mobile, is_primary=True)
                created = True

            if device_id:
                DevicePhoneRelation.objects.create(device_id=device_id, phone=full_phone)
                blacklisted = register_device_phone_attempt(device_id, full_phone)
                if blacklisted:
                    return error_response(message="设备触发风控限制", status_code=403, code=403)

        token = RefreshToken.for_user(user)
        return success_response(
            {
                "created": created,
                "access": str(token.access_token),
                "refresh": str(token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "mobile": _mask_mobile(full_phone),
                    "country_code": country_code,
                },
            }
        )


class UserAccountDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="账号注销（软删除）")
    def delete(self, request):
        serializer = AccountDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        binding = UserPhoneBinding.objects.filter(user=user).first()
        if not binding:
            return error_response(message="未绑定手机号", status_code=400)
        full_phone = f"+{binding.country_code}{binding.phone_number}"
        ok, err_msg, status_code = verify_sms_code_with_lua(full_phone, serializer.validated_data["code"])
        if not ok:
            return error_response(message=err_msg or "验证码错误", status_code=status_code, code=status_code)

        old_username = user.username
        anonymized = f"{old_username}__deleted__{int(time.time())}"
        with transaction.atomic():
            user.is_active = False
            user.username = anonymized[:180]
            user.save(update_fields=["is_active", "username"])
            binding.phone_number = f"{binding.phone_number}__{int(time.time())}"[:20]
            binding.save(update_fields=["phone_number", "updated_at"])
            AccountDeletionLog.objects.create(
                user=user,
                original_username=old_username,
                anonymized_username=user.username,
                reason=serializer.validated_data.get("reason", ""),
            )
        return success_response({"deleted": True})


class PhoneRebindAppealCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="手机号换绑申诉")
    def post(self, request):
        serializer = PhoneRebindAppealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(user=request.user)
        return success_response(PhoneRebindAppealSerializer(obj).data, status_code=201)


class SmsChannelStatsView(APIView):
    permission_classes = [IsAuthenticated, IsOpsAdmin]

    @extend_schema(summary="短信通道到达率统计")
    def get(self, request):
        serializer = SmsChannelStatsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        days = serializer.validated_data["days"]
        since = timezone.now() - timedelta(days=days)
        queryset = SmsDispatchLog.objects.filter(requested_at__gte=since)
        stats = {}
        for row in queryset:
            p = row.provider
            stats.setdefault(p, {"total": 0, "delivered": 0, "failed": 0})
            stats[p]["total"] += 1
            if row.status == SmsDispatchLog.STATUS_DELIVERED:
                stats[p]["delivered"] += 1
            elif row.status == SmsDispatchLog.STATUS_FAILED:
                stats[p]["failed"] += 1
        for provider, payload in stats.items():
            total = payload["total"] or 1
            payload["reach_rate"] = round(payload["delivered"] / total, 4)
        return success_response({"days": days, "channels": stats})


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
        data = OrderSerializer(current_page.object_list, many=True, context={"request": request}).data
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


class OrderAddressUpdateView(APIView):
    permission_classes = [IsAuthenticated, HasOrderEditPermission]

    @extend_schema(summary="手动修改订单地址（需 order_edit 权限）")
    def put(self, request, order_id):
        obj = get_object_or_404(Order, id=order_id)
        serializer = OrderAddressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        update_fields = []
        for field in ("recipient_name", "recipient_phone", "shipping_address"):
            if field in payload:
                setattr(obj, field, payload[field])
                update_fields.append(field)
        if not update_fields:
            return error_response(message="至少传入一个地址字段", status_code=400)
        obj.save(update_fields=update_fields + ["updated_at"])
        return success_response(OrderSerializer(obj, context={"request": request}).data)


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
        client = get_logistics_aggregator_client()
        events = client.fetch_tracking_events(waybill_no=row.waybill_no, carrier=row.carrier)
        if events:
            latest = events[0]
            latest_status = str(latest.get("status") or "").strip()
            row.latest_event = latest_status or row.latest_event
            delivered_markers = {"投递成功", "已签收", "signed", "delivered"}
            normalized_marker = latest_status.lower()
            is_delivered = latest_status in delivered_markers or normalized_marker in delivered_markers
            if is_delivered:
                row.status = LogisticsShipment.STATUS_DELIVERED
                row.order.status = Order.STATUS_SIGNED
                row.order.save(update_fields=["status", "updated_at"])
                row.save(update_fields=["latest_event", "status", "updated_at"])
            else:
                row.save(update_fields=["latest_event", "updated_at"])
        else:
            events = [
                {
                    "time": row.updated_at.date().isoformat(),
                    "status": row.latest_event or "运输中",
                    "location": "",
                }
            ]
        # 统一轨迹格式：[{"time":"2026-04-16","status":"已揽收","location":"深圳"}]
        data = {"waybill_no": row.waybill_no, "carrier": row.carrier, "status": row.status, "tracks": events}
        return success_response(data)


class LogisticsWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(summary="物流平台 Webhook 回调")
    def post(self, request):
        expected_token = (getattr(settings, "LOGISTICS_WEBHOOK_TOKEN", "") or "").strip()
        provided_token = (request.headers.get("X-Webhook-Token", "") or "").strip()
        if expected_token and expected_token != provided_token:
            return error_response(message="invalid webhook token", status_code=403, code=403)

        payload = request.data if isinstance(request.data, dict) else {}

        def _pick_waybill(data: dict) -> str:
            for key in ("waybill_no", "tracking_no", "trackingNo", "tracking_number", "number"):
                val = str(data.get(key) or "").strip()
                if val:
                    return val
            data_list = data.get("data")
            if isinstance(data_list, list) and data_list:
                item = data_list[0] if isinstance(data_list[0], dict) else {}
                for key in ("waybill_no", "tracking_no", "trackingNo", "tracking_number", "number"):
                    val = str(item.get(key) or "").strip()
                    if val:
                        return val
            return ""

        waybill_no = _pick_waybill(payload)
        if not waybill_no:
            return error_response(message="waybill_no is required", status_code=400)
        try:
            shipment = LogisticsShipment.objects.select_related("order").get(waybill_no=waybill_no)
        except LogisticsShipment.DoesNotExist:
            return success_response({"ok": True, "ignored": True, "reason": "unknown waybill_no"})

        def _normalize_events(data: dict):
            if isinstance(data.get("events"), list):
                return [e for e in data.get("events") if isinstance(e, dict)]
            data_list = data.get("data")
            if isinstance(data_list, list) and data_list:
                item = data_list[0] if isinstance(data_list[0], dict) else {}
                track_info = item.get("track_info") if isinstance(item.get("track_info"), dict) else {}
                tracking = track_info.get("tracking")
                if isinstance(tracking, list):
                    normalized = []
                    for e in tracking:
                        if not isinstance(e, dict):
                            continue
                        normalized.append(
                            {
                                "time": e.get("track_date") or e.get("time"),
                                "status": e.get("status_description") or e.get("description") or e.get("status"),
                                "location": e.get("location") or "",
                            }
                        )
                    return normalized
            top = {
                "time": data.get("time"),
                "status": data.get("status"),
                "location": data.get("location"),
            }
            return [top]

        events = _normalize_events(payload)
        top_event = events[0] if events else {}
        callback_status = str(top_event.get("status") or "").strip()
        location = str(top_event.get("location") or "").strip()
        event_time_raw = str(top_event.get("time") or timezone.now().isoformat()).strip()

        def _parse_event_time(value: str):
            v = (value or "").strip()
            if not v:
                return None
            dt = parse_datetime(v)
            if dt:
                return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            d = parse_date(v[:10])
            if d:
                return timezone.make_aware(timezone.datetime(d.year, d.month, d.day, 0, 0, 0))
            return None

        delivered_markers = {"投递成功", "已签收", "signed", "delivered"}
        exception_markers = {"异常", "exception", "退回", "failed", "undelivered"}
        normalized_marker = callback_status.lower()
        is_delivered = callback_status in delivered_markers or normalized_marker in delivered_markers
        is_exception = callback_status in exception_markers or normalized_marker in exception_markers

        with transaction.atomic():
            for e in events[:50]:
                status_text = str(e.get("status") or "").strip()
                location_text = str(e.get("location") or "").strip()
                time_raw = str(e.get("time") or "").strip() or event_time_raw
                LogisticsTrackingEvent.objects.get_or_create(
                    shipment=shipment,
                    event_time_raw=time_raw[:64],
                    status=status_text[:255],
                    location=location_text[:255],
                    source="webhook",
                    defaults={
                        "event_time": _parse_event_time(time_raw),
                        "raw_payload": e if isinstance(e, dict) else {},
                    },
                )

            shipment.latest_event = f"{event_time_raw[:32]} {callback_status} {location}".strip()
            if is_delivered:
                shipment.status = LogisticsShipment.STATUS_DELIVERED
            elif is_exception:
                shipment.status = LogisticsShipment.STATUS_EXCEPTION
            else:
                shipment.status = LogisticsShipment.STATUS_IN_TRANSIT
            shipment.save(update_fields=["latest_event", "status", "updated_at"])

            if is_delivered and shipment.order.status != Order.STATUS_SIGNED:
                shipment.order.status = Order.STATUS_SIGNED
                shipment.order.save(update_fields=["status", "updated_at"])

        return success_response({"ok": True, "delivered": is_delivered, "exception": is_exception, "order_id": shipment.order_id})


class FreightEstimateView(APIView):
    permission_classes = _BUSINESS_API_PERMISSIONS

    @extend_schema(summary="物流运费预估（体积重+目的地）")
    def post(self, request):
        serializer = FreightEstimateQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        divisor = int(getattr(settings, "LOGISTICS_VOLUME_DIVISOR", 6000))
        volume_weight = (payload["length_cm"] * payload["width_cm"] * payload["height_cm"]) / divisor
        chargeable_weight = max(payload["actual_weight_kg"], volume_weight)
        destination_country = str(payload["destination_country"]).upper()
        carrier = (payload.get("carrier") or "").strip()

        queryset = LogisticsRateCard.objects.filter(destination_country=destination_country, is_active=True)
        if carrier:
            queryset = queryset.filter(carrier=carrier)
        cards = list(queryset.order_by("carrier"))
        quotes = get_logistics_aggregator_client().estimate_quotes(
            chargeable_weight_kg=chargeable_weight,
            destination_country=destination_country,
            carrier=carrier,
        )
        for item in quotes:
            item.setdefault("source", "aggregator_api")
        for card in cards:
            extra_weight = max(chargeable_weight - card.base_weight_kg, 0)
            estimated_price = card.base_price + (extra_weight * card.additional_price_per_kg)
            quotes.append(
                {
                    "carrier": card.carrier,
                    "destination_country": card.destination_country,
                    "currency": card.currency,
                    "estimated_price": round(float(estimated_price), 2),
                    "source": "rate_card",
                }
            )
        return success_response(
            {
                "actual_weight_kg": float(payload["actual_weight_kg"]),
                "volume_weight_kg": round(float(volume_weight), 3),
                "chargeable_weight_kg": round(float(chargeable_weight), 3),
                "divisor": divisor,
                "destination_country": destination_country,
                "quotes": quotes,
                "rate_cards": LogisticsRateCardSerializer(cards, many=True).data if cards else [],
            }
        )
