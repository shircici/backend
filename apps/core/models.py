from django.core.cache import cache
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from .services import TokenCipherService


PLATFORM_CHOICES = (
    ("tiktok", "TikTok Shop"),
    ("amazon", "Amazon"),
    ("1688", "1688"),
)


class PlatformToken(models.Model):
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    account_id = models.CharField(max_length=128, default="default", db_index=True)
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField()
    expires_at = models.DateTimeField(db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("platform", "account_id")

    @property
    def access_token(self):
        return TokenCipherService.decrypt(self.access_token_encrypted)

    @property
    def refresh_token(self):
        return TokenCipherService.decrypt(self.refresh_token_encrypted)

    def set_tokens(self, access_token: str, refresh_token: str):
        self.access_token_encrypted = TokenCipherService.encrypt(access_token)
        self.refresh_token_encrypted = TokenCipherService.encrypt(refresh_token)

    def cache_tokens(self):
        cache_key = f"platform_token:{self.platform}:{self.account_id}"
        cache.set(
            cache_key,
            {
                "access_token_encrypted": self.access_token_encrypted,
                "refresh_token_encrypted": self.refresh_token_encrypted,
                "expires_at": self.expires_at.isoformat(),
            },
            timeout=3600,
        )


class Product(models.Model):
    """
    Sharding recommendation for 10M+ SKU:
    - Use hash partitioning key: hash(platform + platform_product_id)
    - Keep local index on platform, platform_product_id, updated_at.
    """

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    platform_product_id = models.CharField(max_length=128, db_index=True)
    title = models.CharField(max_length=500)
    images = models.JSONField(default=list, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ("platform", "platform_product_id")
        indexes = [
            models.Index(fields=["platform", "platform_product_id"]),
            models.Index(fields=["platform", "updated_at"]),
        ]


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    sku = models.CharField(max_length=128, db_index=True)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    attributes = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["product", "sku"])]


class InventorySyncLog(models.Model):
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    warehouse_id = models.CharField(max_length=64, db_index=True)
    total_items = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)
    message = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class CollectionTask(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    target_ids = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    result_message = models.CharField(max_length=500, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)


class SyncRule(models.Model):
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    warehouse_id = models.CharField(max_length=64, db_index=True)
    sync_enabled = models.BooleanField(default=True, db_index=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("platform", "warehouse_id")

    def mark_synced(self):
        self.last_sync_at = timezone.now()
        self.save(update_fields=["last_sync_at"])


class DeadLetterTask(models.Model):
    STATUS_PENDING = "pending"
    STATUS_REPLAYED = "replayed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_REPLAYED, "Replayed"),
    )

    task_name = models.CharField(max_length=128, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField()
    retry_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)


class ApiIdempotencyRecord(models.Model):
    idem_key = models.CharField(max_length=128, unique=True)
    endpoint = models.CharField(max_length=255, db_index=True)
    request_hash = models.CharField(max_length=64, db_index=True)
    response_data = models.JSONField(default=dict, blank=True)
    status_code = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class ReplayAuditLog(models.Model):
    dead_letter_task = models.ForeignKey(DeadLetterTask, on_delete=models.CASCADE, related_name="replay_logs")
    operator = models.CharField(max_length=128, default="system", db_index=True)
    result = models.CharField(max_length=32, default="success", db_index=True)
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class Shop(models.Model):
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    external_shop_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=32, default="active", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BaseOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_SIGNED = "signed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_SIGNED, "Signed"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    order_no = models.CharField(max_length=128, db_index=True)
    buyer_name = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recipient_name = models.CharField(max_length=128, blank=True, default="")
    recipient_phone = models.CharField(max_length=32, blank=True, default="")
    shipping_address = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class Order(BaseOrder):
    class Meta:
        unique_together = ("platform", "order_no")
        permissions = (
            ("order_edit", "Can manually edit order address"),
        )


class PlatformOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="platform_payloads")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, db_index=True)
    platform_order_id = models.CharField(max_length=128, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("platform", "platform_order_id")
        indexes = [
            models.Index(fields=["order", "platform", "synced_at"]),
        ]


class LogisticsShipment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_IN_TRANSIT = "in_transit"
    STATUS_DELIVERED = "delivered"
    STATUS_EXCEPTION = "exception"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_TRANSIT, "In Transit"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_EXCEPTION, "Exception"),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    waybill_no = models.CharField(max_length=128, unique=True, db_index=True)
    carrier = models.CharField(max_length=64, default="mock-express")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    latest_event = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LogisticsRateCard(models.Model):
    carrier = models.CharField(max_length=64, db_index=True)
    destination_country = models.CharField(max_length=8, db_index=True)
    base_weight_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0.5)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="CNY")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["carrier", "destination_country", "is_active"]),
        ]


User = get_user_model()


class UserPhoneBinding(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="phone_binding")
    country_code = models.CharField(max_length=8, default="86", db_index=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    is_primary = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("country_code", "phone_number")
        indexes = [
            models.Index(fields=["country_code", "phone_number"]),
        ]

    @property
    def full_phone(self) -> str:
        return f"+{self.country_code}{self.phone_number}"


class AccountDeletionLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deletion_logs")
    original_username = models.CharField(max_length=150, db_index=True)
    anonymized_username = models.CharField(max_length=180, db_index=True)
    reason = models.CharField(max_length=255, default="", blank=True)
    deleted_at = models.DateTimeField(auto_now_add=True, db_index=True)


class SmsDispatchLog(models.Model):
    STATUS_SENDING = "sending"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_SENDING, "Sending"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_FAILED, "Failed"),
    )
    TYPE_SMS = "sms"
    TYPE_VOICE = "voice"
    TYPE_CHOICES = (
        (TYPE_SMS, "SMS"),
        (TYPE_VOICE, "Voice"),
    )
    PROVIDER_ALIYUN = "aliyun"
    PROVIDER_TENCENT = "tencent"
    PROVIDER_MOCK = "mock"

    phone = models.CharField(max_length=32, db_index=True)
    message_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_SMS)
    provider = models.CharField(max_length=32, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SENDING, db_index=True)
    biz_id = models.CharField(max_length=128, default="", blank=True)
    error_reason = models.CharField(max_length=255, default="", blank=True)
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True, db_index=True)


class PhoneRebindAppeal(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phone_rebind_appeals")
    current_country_code = models.CharField(max_length=8, default="86")
    current_phone_number = models.CharField(max_length=20)
    requested_country_code = models.CharField(max_length=8)
    requested_phone_number = models.CharField(max_length=20)
    proof_material_urls = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    reviewer = models.CharField(max_length=128, default="", blank=True)
    review_note = models.CharField(max_length=255, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)


class DevicePhoneRelation(models.Model):
    device_id = models.CharField(max_length=128, db_index=True)
    phone = models.CharField(max_length=32, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
