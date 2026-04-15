from decimal import Decimal

from rest_framework import serializers

from .models import Sku


class SkuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sku
        fields = [
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
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SkuBulkCreateItemSerializer(serializers.Serializer):
    sku_code = serializers.CharField(max_length=64)
    product_id = serializers.IntegerField()
    product_name = serializers.CharField(max_length=255)
    category_id = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    stock = serializers.IntegerField(min_value=0)
    status = serializers.IntegerField(required=False, default=1)

    def validate_price(self, value: Decimal):
        if value < 0:
            raise serializers.ValidationError("price must be >= 0")
        return value


class SkuBulkCreateSerializer(serializers.Serializer):
    items = SkuBulkCreateItemSerializer(many=True, allow_empty=False)


class SkuBulkUpdateSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    stock = serializers.IntegerField(required=False, min_value=0)
    status = serializers.IntegerField(required=False)
    price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    cost = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, allow_null=True)

    def validate(self, attrs):
        updatable_fields = {"stock", "status", "price", "cost"}
        if not any(field in attrs for field in updatable_fields):
            raise serializers.ValidationError("At least one updatable field is required.")
        return attrs


class SkuBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
