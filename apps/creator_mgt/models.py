from django.db import models


class Creator(models.Model):
    platform_uid = models.CharField(max_length=64, unique=True)
    handle = models.CharField(max_length=64)
    region = models.CharField(max_length=32, blank=True)
    tier = models.CharField(max_length=16, blank=True)
    email = models.EmailField(blank=True)
    whatsapp = models.CharField(max_length=32, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.handle}({self.platform_uid})"


class CreatorEcomProfile(models.Model):
    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="ecom_profile")
    audience_age_json = models.JSONField(default=dict, blank=True)
    audience_gender_json = models.JSONField(default=dict, blank=True)
    amazon_storefront_url = models.URLField(blank=True)
    tiktok_shop_gpm = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    trend_timeseries_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_ecom_profile"
        ordering = ["-id"]


class CreatorAIInsight(models.Model):
    creator = models.OneToOneField(Creator, on_delete=models.CASCADE, related_name="ai_insight")
    style_tags = models.JSONField(default=list, blank=True)
    competitor_products_json = models.JSONField(default=list, blank=True)
    sentiment_keywords_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_ai_insight"
        ordering = ["-id"]


class FulfillmentAsset(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="fulfillments")
    sample_status = models.CharField(max_length=32, default="pending")
    logistics_no = models.CharField(max_length=64, blank=True)
    logistics_status = models.CharField(max_length=32, blank=True)
    tiktok_auth_code = models.CharField(max_length=256, blank=True)
    asset_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fulfillment_asset"
        ordering = ["-id"]


class DataSyncJob(models.Model):
    JOB_TYPE_CHOICES = (
        ("profile_import", "profile_import"),
        ("audience_sync", "audience_sync"),
        ("ecom_sync", "ecom_sync"),
    )
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("running", "running"),
        ("success", "success"),
        ("failed", "failed"),
    )

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="sync_jobs", null=True, blank=True)
    job_type = models.CharField(max_length=32, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    request_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_data_sync_job"
        ordering = ["-id"]


class AIAnalysisJob(models.Model):
    JOB_TYPE_CHOICES = (
        ("content_analysis", "content_analysis"),
        ("review_mining", "review_mining"),
    )
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("running", "running"),
        ("success", "success"),
        ("failed", "failed"),
    )

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="ai_jobs")
    job_type = models.CharField(max_length=32, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    input_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_ai_analysis_job"
        ordering = ["-id"]


class Invitation(models.Model):
    CHANNEL_CHOICES = (
        ("email", "email"),
        ("whatsapp", "whatsapp"),
        ("instagram_dm", "instagram_dm"),
    )
    STATUS_CHOICES = (
        ("draft", "draft"),
        ("sent", "sent"),
        ("failed", "failed"),
    )

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="invitations")
    channel = models.CharField(max_length=32, choices=CHANNEL_CHOICES)
    target_language = models.CharField(max_length=16, default="en")
    pitch_text = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    provider_message_id = models.CharField(max_length=128, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_invitation"
        ordering = ["-id"]


class FulfillmentOrder(models.Model):
    STATUS_CHOICES = (
        ("created", "created"),
        ("dispatched", "dispatched"),
        ("in_transit", "in_transit"),
        ("delivered", "delivered"),
        ("exception", "exception"),
    )

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="fulfillment_orders")
    sku_code = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField(default=1)
    receiver_name = models.CharField(max_length=64)
    receiver_phone = models.CharField(max_length=32, blank=True)
    receiver_address = models.CharField(max_length=255)
    logistics_provider = models.CharField(max_length=64, blank=True)
    logistics_no = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="created")
    tracking_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "creator_fulfillment_order"
        ordering = ["-id"]
