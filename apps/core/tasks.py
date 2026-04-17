from datetime import timedelta
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    CollectionTask,
    DeadLetterTask,
    InventorySyncLog,
    Order,
    PlatformOrder,
    PlatformToken,
    Product,
    SmsDispatchLog,
    SyncRule,
)
from .platform_clients import PlatformRateLimitError, get_platform_client
from .sms_providers import SmsSendError, get_sms_provider
from .services import build_expire_time

logger = logging.getLogger(__name__)


def _record_dead_letter(task_name: str, payload: dict, error: Exception, retry_count: int = 0):
    DeadLetterTask.objects.create(
        task_name=task_name,
        payload=payload,
        error_message=str(error),
        retry_count=retry_count,
    )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def execute_collection_task(self, task_id):
    logger.info("collection task started task_id=%s", task_id)
    task = CollectionTask.objects.get(id=task_id)
    task.status = "running"
    task.save(update_fields=["status", "updated_at"])

    try:
        client = get_platform_client(task.platform)
        products_data = client.fetch_products(task.target_ids)
        with transaction.atomic():
            for row in products_data:
                Product.objects.update_or_create(
                    platform=task.platform,
                    platform_product_id=row["platform_product_id"],
                    defaults={
                        "title": row["title"],
                        "images": row["images"],
                        "attributes": row["attributes"],
                        "price": row["price"],
                        "stock": row["stock"],
                    },
                )
        task.status = "success"
        task.result_message = f"Collected {len(products_data)} products."
        task.save(update_fields=["status", "result_message", "updated_at"])
        logger.info("collection task success task_id=%s total=%s", task_id, len(products_data))
    except Exception as exc:
        task.status = "failed"
        task.result_message = str(exc)
        task.save(update_fields=["status", "result_message", "updated_at"])
        _record_dead_letter("execute_collection_task", {"task_id": task_id}, exc, getattr(self.request, "retries", 0))
        logger.exception("collection task failed task_id=%s error=%s", task_id, exc)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def refresh_platform_token(self, token_id):
    try:
        logger.info("token refresh started token_id=%s", token_id)
        token_obj = PlatformToken.objects.get(id=token_id)
        client = get_platform_client(token_obj.platform)
        refreshed = client.refresh_token(token_obj.refresh_token)
        token_obj.set_tokens(refreshed["access_token"], refreshed["refresh_token"])
        token_obj.expires_at = build_expire_time(refreshed["expires_in"])
        token_obj.save()
        token_obj.cache_tokens()
        logger.info("token refresh success token_id=%s platform=%s", token_id, token_obj.platform)
        return {"token_id": token_obj.id, "platform": token_obj.platform}
    except Exception as exc:
        _record_dead_letter("refresh_platform_token", {"token_id": token_id}, exc, getattr(self.request, "retries", 0))
        logger.exception("token refresh failed token_id=%s error=%s", token_id, exc)
        raise


@shared_task
def refresh_expiring_tokens():
    threshold = timezone.now() + timedelta(minutes=30)
    expiring_tokens = PlatformToken.objects.filter(expires_at__lte=threshold)
    for token_obj in expiring_tokens.iterator():
        refresh_platform_token.delay(token_obj.id)
    return {"queued": expiring_tokens.count()}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_inventory_by_rule(self, sync_rule_id):
    try:
        logger.info("inventory sync started sync_rule_id=%s", sync_rule_id)
        rule = SyncRule.objects.get(id=sync_rule_id)
        client = get_platform_client(rule.platform)
        inventory_data = client.fetch_inventory(rule.warehouse_id)
        success_count = 0
        fail_count = 0

        for row in inventory_data:
            updated = Product.objects.filter(
                platform=rule.platform, platform_product_id=row["platform_product_id"]
            ).update(stock=row["stock"])
            if updated:
                success_count += 1
            else:
                fail_count += 1

        InventorySyncLog.objects.create(
            platform=rule.platform,
            warehouse_id=rule.warehouse_id,
            total_items=len(inventory_data),
            success_count=success_count,
            fail_count=fail_count,
            message="Inventory sync done",
        )
        rule.mark_synced()
        logger.info(
            "inventory sync success sync_rule_id=%s success=%s fail=%s",
            sync_rule_id,
            success_count,
            fail_count,
        )
        return {"sync_rule_id": rule.id, "success_count": success_count, "fail_count": fail_count}
    except Exception as exc:
        _record_dead_letter("sync_inventory_by_rule", {"sync_rule_id": sync_rule_id}, exc, getattr(self.request, "retries", 0))
        logger.exception("inventory sync failed sync_rule_id=%s error=%s", sync_rule_id, exc)
        raise


@shared_task
def scheduled_inventory_sync():
    rules = SyncRule.objects.filter(sync_enabled=True)
    for rule in rules.iterator():
        sync_inventory_by_rule.delay(rule.id)
    return {"queued_rules": rules.count()}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def send_sms_with_failover(self, phone: str, code: str, message_type: str = "sms"):
    providers = getattr(settings, "SMS_PROVIDER_CHAIN", ["aliyun", "tencent"])
    if isinstance(providers, str):
        providers = [p.strip() for p in providers.split(",") if p.strip()]
    providers = providers or ["mock"]
    dispatch = SmsDispatchLog.objects.create(
        phone=phone,
        message_type=message_type,
        provider=providers[0],
        status=SmsDispatchLog.STATUS_SENDING,
    )
    last_error = ""
    for provider_name in providers:
        try:
            provider = get_sms_provider(provider_name)
            result = provider.send_code(phone=phone, code=code, message_type=message_type)
            dispatch.provider = result.provider
            dispatch.biz_id = result.biz_id or ""
            dispatch.status = SmsDispatchLog.STATUS_DELIVERED
            dispatch.delivered_at = timezone.now()
            dispatch.error_reason = ""
            dispatch.save(update_fields=["provider", "biz_id", "status", "delivered_at", "error_reason"])
            return {"ok": True, "provider": result.provider, "biz_id": result.biz_id}
        except SmsSendError as exc:
            last_error = str(exc)
            logger.warning("sms provider failed provider=%s phone=%s err=%s", provider_name, phone, last_error)
            continue
        except Exception as exc:
            last_error = str(exc)
            logger.exception("sms provider runtime error provider=%s phone=%s err=%s", provider_name, phone, last_error)
            continue
    dispatch.status = SmsDispatchLog.STATUS_FAILED
    dispatch.error_reason = last_error or "all providers failed"
    dispatch.save(update_fields=["status", "error_reason"])
    raise SmsSendError(dispatch.error_reason)


def _extract_tiktok_order_defaults(raw_order: dict):
    amount = raw_order.get("payment_total") or raw_order.get("order_amount") or 0
    buyer_name = raw_order.get("buyer_name") or raw_order.get("buyer", {}).get("name") or ""
    status_value = str(raw_order.get("status") or Order.STATUS_PENDING).lower()
    allowed_status = {item[0] for item in Order.STATUS_CHOICES}
    if status_value not in allowed_status:
        status_value = Order.STATUS_PENDING
    return {
        "buyer_name": buyer_name,
        "status": status_value,
        "amount": amount,
        "recipient_name": raw_order.get("recipient_name") or raw_order.get("address", {}).get("name") or "",
        "recipient_phone": raw_order.get("recipient_phone") or raw_order.get("address", {}).get("phone") or "",
        "shipping_address": raw_order.get("address") or {},
    }


@shared_task(bind=True, max_retries=6, retry_backoff=True, retry_jitter=True)
def poll_tiktok_orderlist(self, token_id: int, cursor: str = "", page_size: int = 50):
    token_obj = PlatformToken.objects.get(id=token_id, platform="tiktok")
    client = get_platform_client("tiktok")
    try:
        data = client.fetch_order_list(token_obj.access_token, page_size=page_size, cursor=cursor)
    except PlatformRateLimitError as exc:
        logger.warning("tiktok orderlist rate limit token_id=%s retry_after=%s", token_id, exc.retry_after)
        raise self.retry(countdown=exc.retry_after, exc=exc)
    orders = data.get("orders", [])
    with transaction.atomic():
        for row in orders:
            platform_order_id = str(
                row.get("order_id")
                or row.get("platform_order_id")
                or row.get("id")
                or ""
            ).strip()
            if not platform_order_id:
                continue
            order_no = str(row.get("order_no") or platform_order_id)
            order, _ = Order.objects.update_or_create(
                platform="tiktok",
                order_no=order_no,
                defaults=_extract_tiktok_order_defaults(row),
            )
            PlatformOrder.objects.update_or_create(
                platform="tiktok",
                platform_order_id=platform_order_id,
                defaults={
                    "order": order,
                    "raw_payload": row,
                },
            )
    return {
        "token_id": token_id,
        "count": len(orders),
        "next_cursor": data.get("next_cursor", ""),
        "has_more": data.get("has_more", False),
    }


@shared_task
def schedule_tiktok_order_polling():
    tokens = PlatformToken.objects.filter(platform="tiktok")
    page_size = int(getattr(settings, "TIKTOK_ORDERLIST_PAGE_SIZE", 50))
    for token_obj in tokens.iterator():
        poll_tiktok_orderlist.delay(token_obj.id, cursor="", page_size=page_size)
    return {"queued_tokens": tokens.count()}
