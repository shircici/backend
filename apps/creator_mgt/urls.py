from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AIMultilingualPitchView,
    AIAnalysisJobStatusView,
    AssetUploadCallbackView,
    AssetUploadUrlView,
    ContentAnalysisJobCreateView,
    CreatorAudienceSyncView,
    CreatorAIInsightViewSet,
    CreatorEcomSyncView,
    CreatorEcomProfileViewSet,
    CreatorImportView,
    CreatorTikTokAuthCallbackView,
    CreatorTikTokAuthLoginView,
    CreatorSearchView,
    CreatorViewSet,
    DashboardAggregateView,
    FulfillmentAuthorizeView,
    FulfillmentAssetViewSet,
    FulfillmentDispatchView,
    FulfillmentOrderViewSet,
    FulfillmentTrackingView,
    InvitationHistoryView,
    InvitationSendView,
    LogisticsWebhookView,
    ReviewMiningJobCreateView,
)

router = DefaultRouter()
router.register("creators", CreatorViewSet, basename="creators")
router.register("creator-ecom-profiles", CreatorEcomProfileViewSet, basename="creator-ecom-profiles")
router.register("creator-ai-insights", CreatorAIInsightViewSet, basename="creator-ai-insights")
router.register("fulfillment-assets", FulfillmentAssetViewSet, basename="fulfillment-assets")
router.register("fulfillment-orders", FulfillmentOrderViewSet, basename="fulfillment-orders")

urlpatterns = [
    path("", include(router.urls)),
    path("ai/multilingual-pitch/", AIMultilingualPitchView.as_view(), name="ai-multilingual-pitch"),
    path("ai/content-analysis/jobs/", ContentAnalysisJobCreateView.as_view(), name="content-analysis-job-create"),
    path("ai/review-mining/jobs/", ReviewMiningJobCreateView.as_view(), name="review-mining-job-create"),
    path("ai/jobs/<int:job_id>/", AIAnalysisJobStatusView.as_view(), name="ai-job-status"),
    path("creators/import/platform/", CreatorImportView.as_view(), name="creator-import-platform"),
    path("creators/auth/tiktok/login/", CreatorTikTokAuthLoginView.as_view(), name="creator-tiktok-auth-login"),
    path("creators/auth/tiktok/callback/", CreatorTikTokAuthCallbackView.as_view(), name="creator-tiktok-auth-callback"),
    path("creators/search/", CreatorSearchView.as_view(), name="creator-search"),
    path("creators/<int:creator_id>/sync-audience/", CreatorAudienceSyncView.as_view(), name="creator-sync-audience"),
    path("creators/<int:creator_id>/sync-ecom/", CreatorEcomSyncView.as_view(), name="creator-sync-ecom"),
    path("invitations/<int:creator_id>/send/", InvitationSendView.as_view(), name="invitation-send"),
    path("invitations/<int:creator_id>/history/", InvitationHistoryView.as_view(), name="invitation-history"),
    path("fulfillment-orders/<int:order_id>/dispatch/", FulfillmentDispatchView.as_view(), name="fulfillment-dispatch"),
    path("fulfillment-orders/<int:order_id>/tracking/", FulfillmentTrackingView.as_view(), name="fulfillment-tracking"),
    path("fulfillment-assets/<int:asset_id>/authorize/", FulfillmentAuthorizeView.as_view(), name="asset-authorize"),
    path("assets/upload-url/", AssetUploadUrlView.as_view(), name="asset-upload-url"),
    path("assets/callback/", AssetUploadCallbackView.as_view(), name="asset-upload-callback"),
    path("webhooks/logistics/", LogisticsWebhookView.as_view(), name="logistics-webhook"),
    path("dashboard/creator-board/", DashboardAggregateView.as_view(), name="dashboard-creator-board"),
]
