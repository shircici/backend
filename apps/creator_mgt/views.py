from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import success_response

from .models import (
    AIAnalysisJob,
    Creator,
    CreatorAIInsight,
    CreatorEcomProfile,
    DataSyncJob,
    FulfillmentAsset,
    FulfillmentOrder,
    Invitation,
)
from .serializers import (
    AIPitchSerializer,
    AIAnalysisJobSerializer,
    AssetUploadCallbackSerializer,
    CreatorImportSerializer,
    CreatorAIInsightSerializer,
    CreatorEcomProfileSerializer,
    CreatorSerializer,
    DispatchOrderSerializer,
    FulfillmentAuthorizeSerializer,
    FulfillmentAssetSerializer,
    FulfillmentOrderSerializer,
    InvitationSendSerializer,
    InvitationSerializer,
    SimpleCreatorIDSerializer,
)
from .services import (
    build_creator_dashboard_payload,
    build_multilingual_pitch,
    build_tiktok_authorize_url,
    build_tracking_payload,
    exchange_tiktok_code,
)


class BaseModelViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return success_response(data=response.data)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return success_response(data=response.data, status_code=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return success_response(data=response.data)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return success_response(data=response.data)

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return success_response(data=response.data)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return success_response(data=None, message="deleted")


class CreatorViewSet(BaseModelViewSet):
    queryset = Creator.objects.all()
    serializer_class = CreatorSerializer


class CreatorEcomProfileViewSet(BaseModelViewSet):
    queryset = CreatorEcomProfile.objects.select_related("creator").all()
    serializer_class = CreatorEcomProfileSerializer


class CreatorAIInsightViewSet(BaseModelViewSet):
    queryset = CreatorAIInsight.objects.select_related("creator").all()
    serializer_class = CreatorAIInsightSerializer


class FulfillmentAssetViewSet(BaseModelViewSet):
    queryset = FulfillmentAsset.objects.select_related("creator").all()
    serializer_class = FulfillmentAssetSerializer


class AIMultilingualPitchView(APIView):
    @extend_schema(summary="AI 多语种邀约接口")
    def post(self, request):
        serializer = AIPitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator_id = serializer.validated_data["creator_id"]
        target_language = serializer.validated_data["target_language"]
        creator = get_object_or_404(Creator, pk=creator_id)
        pitch = build_multilingual_pitch(creator=creator, target_language=target_language)
        return success_response(data={"creator_id": creator.id, "target_language": target_language, "pitch": pitch})


class DashboardAggregateView(APIView):
    @extend_schema(summary="看板聚合查询接口")
    def get(self, request):
        items = build_creator_dashboard_payload()
        return success_response(data={"items": items})


class CreatorTikTokAuthLoginView(APIView):
    @extend_schema(summary="达人模块 - 获取 TikTok 授权 URL")
    def get(self, request):
        redirect_uri = request.query_params.get("redirect_uri", "").strip()
        if not redirect_uri:
            raise ValidationError("redirect_uri is required")
        scope = request.query_params.get("scope", "user.info.basic")
        state = request.query_params.get("state", "creator-mgt-tiktok")
        login_url = build_tiktok_authorize_url(
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
        )
        return success_response(data={"platform": "tiktok", "authorization_url": login_url, "state": state})


class CreatorTikTokAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="达人模块 - TikTok OAuth 回调并保存 Token")
    def get(self, request):
        code = request.query_params.get("code")
        redirect_uri = request.query_params.get("redirect_uri", "").strip()
        if not code:
            raise ValidationError("code is required")
        if not redirect_uri:
            raise ValidationError("redirect_uri is required")
        token_payload = exchange_tiktok_code(code=code, redirect_uri=redirect_uri)
        data = token_payload.get("data") if isinstance(token_payload, dict) else None
        return success_response(
            data={
                "platform": "tiktok",
                "open_id": data.get("open_id") if isinstance(data, dict) else None,
                "scope": data.get("scope") if isinstance(data, dict) else None,
                "expires_in": data.get("expires_in") if isinstance(data, dict) else None,
                "access_token": data.get("access_token") if isinstance(data, dict) else None,
                "refresh_token": data.get("refresh_token") if isinstance(data, dict) else None,
                "raw": token_payload,
            }
        )


class CreatorImportView(APIView):
    @extend_schema(summary="按平台信息导入达人")
    def post(self, request):
        serializer = CreatorImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        creator, created = Creator.objects.update_or_create(
            platform_uid=payload["platform_uid"],
            defaults={
                "handle": payload["handle"],
                "region": payload.get("region", ""),
                "tier": payload.get("tier", ""),
                "email": payload.get("email", ""),
                "whatsapp": payload.get("whatsapp", ""),
                "timezone": payload.get("timezone", "UTC") or "UTC",
            },
        )
        job = DataSyncJob.objects.create(
            creator=creator,
            job_type="profile_import",
            status="success",
            request_payload=request.data,
            result_payload={"created": created},
        )
        return success_response(
            data={"creator": CreatorSerializer(creator).data, "job_id": job.id},
            status_code=status.HTTP_201_CREATED,
        )


class CreatorAudienceSyncView(APIView):
    @extend_schema(summary="同步达人粉丝画像")
    def post(self, request, creator_id):
        creator = get_object_or_404(Creator, pk=creator_id)
        job = DataSyncJob.objects.create(
            creator=creator,
            job_type="audience_sync",
            status="success",
            request_payload=request.data,
            result_payload={"synced_fields": ["audience_age_json", "audience_gender_json"]},
        )
        CreatorEcomProfile.objects.update_or_create(
            creator=creator,
            defaults={
                "audience_age_json": {"18-24": 35, "25-34": 41, "35+": 24},
                "audience_gender_json": {"female": 62, "male": 38},
            },
        )
        return success_response(data={"job_id": job.id, "status": job.status})


class CreatorEcomSyncView(APIView):
    @extend_schema(summary="同步达人电商关联数据")
    def post(self, request, creator_id):
        creator = get_object_or_404(Creator, pk=creator_id)
        profile, _ = CreatorEcomProfile.objects.get_or_create(creator=creator)
        profile.amazon_storefront_url = profile.amazon_storefront_url or "https://amazon.example/storefront"
        profile.tiktok_shop_gpm = profile.tiktok_shop_gpm or 1200.00
        profile.trend_timeseries_json = profile.trend_timeseries_json or []
        profile.save()
        job = DataSyncJob.objects.create(
            creator=creator,
            job_type="ecom_sync",
            status="success",
            request_payload=request.data,
            result_payload={"profile_id": profile.id},
        )
        return success_response(data={"job_id": job.id, "status": job.status})


class CreatorSearchView(APIView):
    @extend_schema(summary="达人复合筛选查询")
    def get(self, request):
        queryset = Creator.objects.all().order_by("-id")
        region = request.query_params.get("region")
        tier = request.query_params.get("tier")
        keyword = request.query_params.get("keyword")
        if region:
            queryset = queryset.filter(region=region)
        if tier:
            queryset = queryset.filter(tier=tier)
        if keyword:
            queryset = queryset.filter(handle__icontains=keyword)
        return success_response(data={"items": CreatorSerializer(queryset, many=True).data})


class ContentAnalysisJobCreateView(APIView):
    @extend_schema(summary="触发 AI 内容识别任务")
    def post(self, request):
        serializer = SimpleCreatorIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator = get_object_or_404(Creator, pk=serializer.validated_data["creator_id"])
        job = AIAnalysisJob.objects.create(
            creator=creator,
            job_type="content_analysis",
            status="pending",
            input_payload=request.data,
        )
        return success_response(data={"job_id": job.id, "status": job.status}, status_code=status.HTTP_201_CREATED)


class ReviewMiningJobCreateView(APIView):
    @extend_schema(summary="触发 AI 评论关键词分析任务")
    def post(self, request):
        serializer = SimpleCreatorIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator = get_object_or_404(Creator, pk=serializer.validated_data["creator_id"])
        job = AIAnalysisJob.objects.create(
            creator=creator,
            job_type="review_mining",
            status="pending",
            input_payload=request.data,
        )
        return success_response(data={"job_id": job.id, "status": job.status}, status_code=status.HTTP_201_CREATED)


class AIAnalysisJobStatusView(APIView):
    @extend_schema(summary="查询 AI 任务状态")
    def get(self, request, job_id):
        job = get_object_or_404(AIAnalysisJob, pk=job_id)
        if job.status == "pending":
            job.status = "success"
            job.result_payload = {"summary": "analysis completed", "tags": ["style", "intent"]}
            job.save(update_fields=["status", "result_payload", "updated_at"])
        return success_response(data=AIAnalysisJobSerializer(job).data)


class InvitationSendView(APIView):
    @extend_schema(summary="发送邀约并记录状态")
    def post(self, request, creator_id):
        creator = get_object_or_404(Creator, pk=creator_id)
        serializer = InvitationSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_language = serializer.validated_data["target_language"]
        pitch_text = serializer.validated_data.get("custom_pitch") or build_multilingual_pitch(creator, target_language)
        invitation = Invitation.objects.create(
            creator=creator,
            channel=serializer.validated_data["channel"],
            target_language=target_language,
            pitch_text=pitch_text,
            status="sent",
            provider_message_id=f"msg-{creator.id}-{int(timezone.now().timestamp())}",
            sent_at=timezone.now(),
        )
        return success_response(data=InvitationSerializer(invitation).data, status_code=status.HTTP_201_CREATED)


class InvitationHistoryView(APIView):
    @extend_schema(summary="查询达人邀约历史")
    def get(self, request, creator_id):
        creator = get_object_or_404(Creator, pk=creator_id)
        invitations = Invitation.objects.filter(creator=creator).order_by("-id")
        return success_response(data={"items": InvitationSerializer(invitations, many=True).data})


class FulfillmentOrderViewSet(BaseModelViewSet):
    queryset = FulfillmentOrder.objects.select_related("creator").all()
    serializer_class = FulfillmentOrderSerializer


class FulfillmentDispatchView(APIView):
    @extend_schema(summary="发货并回写物流单号")
    def post(self, request, order_id):
        order = get_object_or_404(FulfillmentOrder, pk=order_id)
        serializer = DispatchOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.logistics_provider = serializer.validated_data["logistics_provider"]
        order.logistics_no = serializer.validated_data["logistics_no"]
        order.status = "dispatched"
        order.save(update_fields=["logistics_provider", "logistics_no", "status", "updated_at"])
        return success_response(data=FulfillmentOrderSerializer(order).data)


class FulfillmentTrackingView(APIView):
    @extend_schema(summary="查询履约物流追踪")
    def get(self, request, order_id):
        order = get_object_or_404(FulfillmentOrder, pk=order_id)
        if not order.logistics_no:
            raise ValidationError("order has not been dispatched")
        tracking_payload = build_tracking_payload(order)
        order.tracking_payload = tracking_payload
        if order.status == "dispatched":
            order.status = "in_transit"
        order.save(update_fields=["tracking_payload", "status", "updated_at"])
        return success_response(data=tracking_payload)


class FulfillmentAuthorizeView(APIView):
    @extend_schema(summary="保存 TikTok Spark Ads 授权码")
    def post(self, request, asset_id):
        asset = get_object_or_404(FulfillmentAsset, pk=asset_id)
        serializer = FulfillmentAuthorizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset.tiktok_auth_code = serializer.validated_data["tiktok_auth_code"]
        asset.save(update_fields=["tiktok_auth_code", "updated_at"])
        return success_response(data=FulfillmentAssetSerializer(asset).data)


class AssetUploadUrlView(APIView):
    @extend_schema(summary="生成素材上传地址（占位）")
    def post(self, request):
        file_name = request.data.get("file_name", "asset.jpg")
        upload_url = f"https://upload.example.com/{file_name}"
        return success_response(data={"upload_url": upload_url, "expires_in": 3600})


class AssetUploadCallbackView(APIView):
    @extend_schema(summary="素材上传完成回调")
    def post(self, request):
        serializer = AssetUploadCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator = get_object_or_404(Creator, pk=serializer.validated_data["creator_id"])
        asset = FulfillmentAsset.objects.create(
            creator=creator,
            asset_url=serializer.validated_data["asset_url"],
            sample_status="uploaded",
        )
        return success_response(data=FulfillmentAssetSerializer(asset).data, status_code=status.HTTP_201_CREATED)


class LogisticsWebhookView(APIView):
    @extend_schema(summary="物流状态回调")
    def post(self, request):
        logistics_no = request.data.get("logistics_no")
        status_value = request.data.get("status")
        order = get_object_or_404(FulfillmentOrder, logistics_no=logistics_no)
        if status_value in {"in_transit", "delivered", "exception"}:
            order.status = status_value
        order.tracking_payload = request.data
        order.save(update_fields=["status", "tracking_payload", "updated_at"])
        return success_response(data={"order_id": order.id, "status": order.status})
