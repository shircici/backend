import base64
import hashlib
import urllib.parse

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Creator, FulfillmentOrder


def build_multilingual_pitch(creator: Creator, target_language: str) -> str:
    return (
        f"Hello {creator.handle}, we love your content. "
        f"This is a {target_language} invitation draft for potential collaboration."
    )


def build_creator_dashboard_payload():
    creators = Creator.objects.all().order_by("-id")
    items = []
    for creator in creators:
        items.append(
            {
                "creator_id": creator.id,
                "handle": creator.handle,
                "region": creator.region,
                "tier": creator.tier,
                "follower_growth_curve": [],
                "heat_index": 0,
            }
        )
    return items


def build_tracking_payload(order: FulfillmentOrder):
    return {
        "logistics_no": order.logistics_no,
        "provider": order.logistics_provider,
        "status": order.status,
        "events": [
            {
                "time": timezone.now().isoformat(),
                "status": order.status,
                "description": "tracking status synced",
            }
        ],
    }


def build_tiktok_oauth_state(seed: str) -> str:
    raw = seed or "creator-mgt"
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def build_tiktok_authorize_url(redirect_uri: str, scope: str, state: str) -> str:
    client_key = getattr(settings, "TIKTOK_CREATOR_APP_KEY", "").strip()
    if not client_key:
        raise ValidationError("TIKTOK_CREATOR_APP_KEY is not configured")
    if not redirect_uri:
        raise ValidationError("redirect_uri is required")

    params = {
        "client_key": client_key,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": build_tiktok_oauth_state(state),
    }
    return f"https://www.tiktok.com/v2/auth/authorize/?{urllib.parse.urlencode(params)}"


def exchange_tiktok_code(code: str, redirect_uri: str) -> dict:
    client_key = getattr(settings, "TIKTOK_CREATOR_APP_KEY", "").strip()
    client_secret = getattr(settings, "TIKTOK_CREATOR_APP_SECRET", "").strip()
    token_url = getattr(settings, "TIKTOK_OAUTH_TOKEN_URL", "https://open.tiktokapis.com/v2/oauth/token/").strip()

    if not client_key or not client_secret:
        raise ValidationError("TikTok app key/secret is not configured")

    response = requests.post(
        token_url,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValidationError(f"TikTok token response is invalid JSON: {exc}") from exc

    if response.status_code >= 400:
        message = payload.get("error_description") or payload.get("message") or "token exchange failed"
        raise ValidationError(f"TikTok token exchange failed: {message}")
    return payload
