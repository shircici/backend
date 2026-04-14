from rest_framework import serializers

from .models import (
    PhoneRebindAppeal,
    CollectionTask,
    InventorySyncLog,
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
