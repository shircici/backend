from django.urls import path

from .views import (
    BatchPreviewListView,
    BatchProgressView,
    CalculateView,
    DemoDecisionCalculateView,
    InfluencerBatchCalculateView,
)

app_name = "selection_engine"

urlpatterns = [
    path("selection/calculate/", CalculateView.as_view(), name="selection-calculate"),
    path("v1/decision/calculate/", DemoDecisionCalculateView.as_view(), name="decision-calculate-compat"),
    path("selection/influencer-batch/", InfluencerBatchCalculateView.as_view(), name="selection-influencer-batch"),
    path("selection/batch/<str:batch_id>/progress/", BatchProgressView.as_view(), name="selection-batch-progress"),
    path("selection/batch/<str:batch_id>/preview/", BatchPreviewListView.as_view(), name="selection-batch-preview"),
]
