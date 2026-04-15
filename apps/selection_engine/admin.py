from django.contrib import admin

from .models import AlgorithmConfig, DecisionLog, InfluencerMatchPreview


@admin.register(AlgorithmConfig)
class AlgorithmConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(DecisionLog)
class DecisionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "product_id", "roas", "decision_label", "created_at")
    list_filter = ("decision_label",)


@admin.register(InfluencerMatchPreview)
class InfluencerMatchPreviewAdmin(admin.ModelAdmin):
    list_display = ("id", "batch_id", "product_id", "influencer_id", "grade", "roas", "created_at")
    list_filter = ("grade",)
