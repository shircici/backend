from rest_framework import serializers

from .models import (
    PhoneRebindAppeal,
    CollectionTask,
    InventorySyncLog,
    LogisticsRateCard,
    LogisticsShipment,
    Order,
    PlatformToken,
    Product,
    ProductVariant,
    SmsDispatchLog,
    Shop,
    SyncRule,
)


class CollectionTaskCreateSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=["tiktok", "amazon", "1688"])
    target_ids = serializers.ListField(child=serializers.CharField(), allow_empty=False)


class Collect1688SingleSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500)
    source = serializers.ChoiceField(choices=["1688"], default="1688")


class Collect1688BatchSerializer(serializers.Serializer):
    urls = serializers.ListField(child=serializers.URLField(max_length=500), allow_empty=False)
    source = serializers.ChoiceField(choices=["1688"], default="1688")


class GoodsListingSerializer(serializers.Serializer):
    goods_id = serializers.IntegerField()
    platform = serializers.ChoiceField(choices=["tiktok", "amazon", "1688"])
    shop_id = serializers.CharField(required=False, allow_blank=True)


class GoodsBatchListingSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    platform = serializers.ChoiceField(choices=["tiktok", "amazon", "1688"])


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
    can_manual_edit_address = serializers.SerializerMethodField()

    def get_can_manual_edit_address(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return False
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.has_perm("core.order_edit")

    class Meta:
        model = Order
        fields = "__all__"


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[s[0] for s in Order.STATUS_CHOICES])


class OrderAddressUpdateSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(max_length=128, required=False, allow_blank=True)
    recipient_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    shipping_address = serializers.JSONField(required=False)


class LogisticsShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticsShipment
        fields = "__all__"


class FreightEstimateSerializer(serializers.Serializer):
    destination = serializers.CharField(max_length=64)
    weight_kg = serializers.FloatField(min_value=0.01)
    length_cm = serializers.FloatField(min_value=0.01)
    width_cm = serializers.FloatField(min_value=0.01)
    height_cm = serializers.FloatField(min_value=0.01)


class LogisticsRateCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticsRateCard
        fields = "__all__"


class FreightEstimateQuerySerializer(serializers.Serializer):
    length_cm = serializers.DecimalField(max_digits=10, decimal_places=2)
    width_cm = serializers.DecimalField(max_digits=10, decimal_places=2)
    height_cm = serializers.DecimalField(max_digits=10, decimal_places=2)
    actual_weight_kg = serializers.DecimalField(max_digits=10, decimal_places=3)
    destination_country = serializers.CharField(max_length=8)
    carrier = serializers.CharField(required=False, allow_blank=True, max_length=64)


class SmsCodeSendSerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\d{6,20}$")
    country_code = serializers.RegexField(regex=r"^\d{1,4}$", required=False, default="86")
    voice = serializers.BooleanField(required=False, default=False)
    captcha_id = serializers.CharField(required=False, allow_blank=True)
    captcha_answer = serializers.CharField(required=False, allow_blank=True)


class SmsCodeVerifySerializer(serializers.Serializer):
    phone = serializers.RegexField(regex=r"^\d{6,20}$")
    code = serializers.RegexField(regex=r"^\d{4,6}$")


class MobileAuthSerializer(serializers.Serializer):
    mobile = serializers.RegexField(regex=r"^\d{6,20}$")
    country_code = serializers.RegexField(regex=r"^\d{1,4}$", required=False, default="86")
    code = serializers.RegexField(regex=r"^\d{4,6}$")
    agreed_privacy = serializers.BooleanField(required=True)


class AccountDeleteSerializer(serializers.Serializer):
    code = serializers.RegexField(regex=r"^\d{4,6}$")
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CarrierOneTapSerializer(serializers.Serializer):
    mobile = serializers.RegexField(regex=r"^\d{6,20}$")
    country_code = serializers.RegexField(regex=r"^\d{1,4}$", required=False, default="86")
    token = serializers.CharField()
    carrier = serializers.CharField(required=False, allow_blank=True)


class PhoneRebindAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneRebindAppeal
        fields = "__all__"
        read_only_fields = ["user", "status", "reviewer", "review_note", "created_at", "updated_at"]


class SmsChannelStatsQuerySerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=30, required=False, default=7)


class SmsDispatchLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsDispatchLog
        fields = "__all__"
