from rest_framework import serializers

from .models import (
    CollectionTask,
    InventorySyncLog,
    LogisticsShipment,
    Order,
    PlatformToken,
    Product,
    ProductVariant,
    Shop,
    SyncRule,
)


class CollectionTaskCreateSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=["tiktok", "amazon", "1688"])
    target_ids = serializers.ListField(child=serializers.CharField(), allow_empty=False)


class CollectionTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionTask
        fields = "__all__"


class PlatformTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformToken
        fields = ["id", "platform", "account_id", "expires_at", "updated_at", "created_at"]


class SyncRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncRule
        fields = "__all__"


class InventorySyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventorySyncLog
        fields = "__all__"


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[s[0] for s in Order.STATUS_CHOICES])


class LogisticsShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticsShipment
        fields = "__all__"
