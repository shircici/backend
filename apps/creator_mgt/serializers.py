from rest_framework import serializers

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


class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Creator
        fields = [
            "id",
            "platform_uid",
            "handle",
            "region",
            "tier",
            "email",
            "whatsapp",
            "timezone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreatorEcomProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorEcomProfile
        fields = [
            "id",
            "creator",
            "audience_age_json",
            "audience_gender_json",
            "amazon_storefront_url",
            "tiktok_shop_gpm",
            "trend_timeseries_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreatorAIInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorAIInsight
        fields = [
            "id",
            "creator",
            "style_tags",
            "competitor_products_json",
            "sentiment_keywords_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FulfillmentAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FulfillmentAsset
        fields = [
            "id",
            "creator",
            "sample_status",
            "logistics_no",
            "logistics_status",
            "tiktok_auth_code",
            "asset_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DataSyncJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSyncJob
        fields = [
            "id",
            "creator",
            "job_type",
            "status",
            "request_payload",
            "result_payload",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "result_payload", "error_message", "created_at", "updated_at"]


class AIAnalysisJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysisJob
        fields = [
            "id",
            "creator",
            "job_type",
            "status",
            "input_payload",
            "result_payload",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "result_payload", "error_message", "created_at", "updated_at"]


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = [
            "id",
            "creator",
            "channel",
            "target_language",
            "pitch_text",
            "status",
            "provider_message_id",
            "sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "provider_message_id", "sent_at", "created_at", "updated_at"]


class FulfillmentOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FulfillmentOrder
        fields = [
            "id",
            "creator",
            "sku_code",
            "quantity",
            "receiver_name",
            "receiver_phone",
            "receiver_address",
            "logistics_provider",
            "logistics_no",
            "status",
            "tracking_payload",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "logistics_provider",
            "logistics_no",
            "status",
            "tracking_payload",
            "created_at",
            "updated_at",
        ]


class CreatorImportSerializer(serializers.Serializer):
    platform_uid = serializers.CharField(max_length=64)
    handle = serializers.CharField(max_length=64)
    region = serializers.CharField(max_length=32, required=False, allow_blank=True)
    tier = serializers.CharField(max_length=16, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    whatsapp = serializers.CharField(max_length=32, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True)


class SimpleCreatorIDSerializer(serializers.Serializer):
    creator_id = serializers.IntegerField()


class AIPitchSerializer(serializers.Serializer):
    creator_id = serializers.IntegerField()
    target_language = serializers.CharField(max_length=16, default="en")


class InvitationSendSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=Invitation.CHANNEL_CHOICES)
    target_language = serializers.CharField(max_length=16, default="en")
    custom_pitch = serializers.CharField(required=False, allow_blank=True)


class DispatchOrderSerializer(serializers.Serializer):
    logistics_provider = serializers.CharField(max_length=64)
    logistics_no = serializers.CharField(max_length=64)


class AssetUploadCallbackSerializer(serializers.Serializer):
    creator_id = serializers.IntegerField()
    asset_url = serializers.URLField()


class FulfillmentAuthorizeSerializer(serializers.Serializer):
    tiktok_auth_code = serializers.CharField(max_length=256)
