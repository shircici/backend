from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.responses import error_response, success_response

from .cache_utils import invalidate_sku_cache, with_cache_breakdown_protection
from .models import Sku
from .pagination import SkuCursorPagination
from .serializers import (
    SkuBulkCreateSerializer,
    SkuBulkDeleteSerializer,
    SkuBulkUpdateSerializer,
    SkuSerializer,
)
from .tasks import export_sku_to_csv


class SkuDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="单个 SKU 查询（Redis缓存 + 防击穿）")
    def get(self, request, sku_code):
        def loader():
            obj = get_object_or_404(
                Sku.objects.only(
                    "id",
                    "sku_code",
                    "product_id",
                    "product_name",
                    "category_id",
                    "price",
                    "cost",
                    "stock",
                    "status",
                    "version",
                    "created_at",
                    "updated_at",
                    "is_deleted",
                ),
                sku_code=sku_code,
                is_deleted=False,
            )
            return SkuSerializer(obj).data

        data = with_cache_breakdown_protection(sku_code=sku_code, loader=loader, ttl=300)
        return success_response(data=data)


class SkuListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = SkuCursorPagination

    @extend_schema(summary="SKU 游标分页查询（过滤 + 排序）")
    def get(self, request):
        queryset = Sku.objects.filter(is_deleted=False).only(
            "id",
            "sku_code",
            "product_id",
            "product_name",
            "category_id",
            "price",
            "cost",
            "stock",
            "status",
            "updated_at",
        )
        category_id = request.query_params.get("category_id")
        status_value = request.query_params.get("status")
        keyword = request.query_params.get("keyword")
        order_by = request.query_params.get("order_by", "-id")
        allowed_order = {"id", "-id", "updated_at", "-updated_at", "price", "-price"}

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if status_value is not None:
            queryset = queryset.filter(status=status_value)
        if keyword:
            # Avoid LIKE '%keyword%' on huge tables in production.
            # Prefer prefix match, FULLTEXT index, or external inverted index (Elasticsearch).
            queryset = queryset.filter(Q(sku_code__icontains=keyword) | Q(product_name__icontains=keyword))
        queryset = queryset.order_by(order_by if order_by in allowed_order else "-id")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = SkuSerializer(page, many=True).data
        return paginator.get_paginated_response({"code": 200, "message": "success", "data": data})


class SkuBulkCreateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="批量创建 SKU（bulk_create 分批）")
    def post(self, request):
        serializer = SkuBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]

        chunk_size = 5000

        created = 0
        with transaction.atomic():
            for i in range(0, len(items), chunk_size):
                batch = items[i : i + chunk_size]
                objs = [
                    Sku(
                        sku_code=item["sku_code"],
                        product_id=item["product_id"],
                        product_name=item["product_name"],
                        category_id=item["category_id"],
                        price=item["price"],
                        cost=item.get("cost"),
                        stock=item["stock"],
                        status=item.get("status", 1),
                    )
                    for item in batch
                ]
                Sku.objects.bulk_create(objs, batch_size=chunk_size, ignore_conflicts=True)
                created += len(objs)
        return success_response(data={"created": created}, status_code=status.HTTP_201_CREATED)


class SkuBulkUpdateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="批量更新 SKU（update + 乐观锁版本自增）")
    def post(self, request):
        serializer = SkuBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        payload = {k: v for k, v in serializer.validated_data.items() if k != "ids"}
        payload["version"] = F("version") + 1

        skus = list(Sku.objects.filter(id__in=ids, is_deleted=False).only("id", "sku_code"))
        updated_count = Sku.objects.filter(id__in=ids, is_deleted=False).update(**payload)
        for sku in skus:
            invalidate_sku_cache(sku.sku_code)
        return success_response(data={"updated": updated_count})


class SkuBulkDeleteView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="批量软删除 SKU（update）")
    def post(self, request):
        serializer = SkuBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        skus = list(Sku.objects.filter(id__in=ids, is_deleted=False).only("id", "sku_code"))
        deleted_count = Sku.objects.filter(id__in=ids, is_deleted=False).update(is_deleted=True, version=F("version") + 1)
        for sku in skus:
            invalidate_sku_cache(sku.sku_code)
        return success_response(data={"deleted": deleted_count})


class SkuSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="SKU 搜索（当前 icontains，建议生产切换 MySQL FULLTEXT/ES）")
    def get(self, request):
        keyword = request.query_params.get("keyword", "").strip()
        if not keyword:
            return error_response(message="keyword is required", status_code=400)

        queryset = (
            Sku.objects.filter(is_deleted=False)
            # Current fallback query; switch to FULLTEXT or ES for 10M+ in production.
            .filter(Q(sku_code__startswith=keyword) | Q(product_name__startswith=keyword))
            .only("id", "sku_code", "product_name", "price", "cost", "stock", "updated_at")
            .order_by("-id")[:200]
        )
        data = SkuSerializer(queryset, many=True).data
        return success_response(data=data)


class SkuExportView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="触发异步导出 SKU CSV")
    def post(self, request):
        async_result = export_sku_to_csv.delay()
        return success_response(data={"task_id": async_result.id})
