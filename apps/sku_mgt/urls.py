from django.urls import path

from .views import (
    SkuBulkCreateView,
    SkuBulkDeleteView,
    SkuBulkUpdateView,
    SkuDetailView,
    SkuExportView,
    SkuListView,
    SkuSearchView,
)

urlpatterns = [
    path("detail/<str:sku_code>/", SkuDetailView.as_view(), name="sku-detail"),
    path("list/", SkuListView.as_view(), name="sku-list"),
    path("bulk-create/", SkuBulkCreateView.as_view(), name="sku-bulk-create"),
    path("bulk-update/", SkuBulkUpdateView.as_view(), name="sku-bulk-update"),
    path("bulk-delete/", SkuBulkDeleteView.as_view(), name="sku-bulk-delete"),
    path("search/", SkuSearchView.as_view(), name="sku-search"),
    path("export/", SkuExportView.as_view(), name="sku-export"),
]
