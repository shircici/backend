from decimal import Decimal

from rest_framework import serializers

from .models import InfluencerMatchPreview


class SelectionCalculateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    promotion_cost = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0"))
    estimated_revenue = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0"))
    commission_rate = serializers.DecimalField(
        max_digits=8,
        decimal_places=6,
        required=False,
        allow_null=True,
        help_text="平台佣金率（0~1）；不传则使用服务端默认",
    )

    def validate_commission_rate(self, value):
        if value is None:
            return value
        if value < 0 or value > 1:
            raise serializers.ValidationError("佣金率需在 0~1 之间")
        return value


class InfluencerMatchPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerMatchPreview
        fields = ("influencer_id", "grade", "roas", "product_id", "detail", "created_at")


class InfluencerBatchSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    influencer_ids = serializers.ListField(
        child=serializers.CharField(max_length=64, allow_blank=False),
        min_length=1,
        max_length=500,
        help_text="达人 ID 列表，最多 500",
    )
