import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests
from django.conf import settings


class PlatformRateLimitError(Exception):
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = max(int(retry_after or 1), 1)


@dataclass
class BasePlatformClient:
    platform: str

    def get_oauth_authorize_url(self, state: str):
        return f"https://auth.{self.platform}.mock/oauth/authorize?client_id=demo&state={state}&response_type=code"

    def exchange_code_for_token(self, code: str):
        timestamp = int(time.time())
        return {
            "access_token": f"{self.platform}_access_{code}_{timestamp}",
            "refresh_token": f"{self.platform}_refresh_{code}_{timestamp}",
            "expires_in": 7200,
            "account_id": "default",
        }

    def refresh_token(self, refresh_token: str):
        timestamp = int(time.time())
        return {
            "access_token": f"{self.platform}_refreshed_access_{timestamp}",
            "refresh_token": f"{self.platform}_refreshed_refresh_{timestamp}",
            "expires_in": 7200,
        }

    def fetch_products(self, target_ids):
        data = []
        for item_id in target_ids:
            data.append(
                {
                    "platform_product_id": str(item_id),
                    "title": f"{self.platform.upper()} Product {item_id}",
                    "images": [f"https://img.mock/{self.platform}/{item_id}.jpg"],
                    "attributes": {"color": "black", "size": "M"},
                    "price": "99.90",
                    "stock": 200,
                }
            )
        return data

    def fetch_inventory(self, warehouse_id: str):
        return [
            {"platform_product_id": "demo-1001", "stock": 88},
            {"platform_product_id": "demo-1002", "stock": 66},
        ]

    def fetch_order_list(self, access_token: str, page_size: int = 50, cursor: str = ""):
        return {"orders": [], "next_cursor": "", "has_more": False}


def get_platform_client(platform: str) -> BasePlatformClient:
    supported = {"tiktok", "amazon", "1688"}
    if platform not in supported:
        raise ValueError(f"Unsupported platform: {platform}")
    if platform == "tiktok":
        return TikTokPlatformClient(platform=platform)
    return BasePlatformClient(platform=platform)


@dataclass
class TikTokPlatformClient(BasePlatformClient):
    def _client_key(self) -> str:
        return (getattr(settings, "TIKTOK_CLIENT_KEY", "") or "").strip()

    def _client_secret(self) -> str:
        return (getattr(settings, "TIKTOK_CLIENT_SECRET", "") or "").strip()

    def _redirect_uri(self) -> str:
        return (getattr(settings, "TIKTOK_REDIRECT_URI", "") or "").strip()

    def _auth_base_url(self) -> str:
        return (getattr(settings, "TIKTOK_AUTH_BASE_URL", "https://www.tiktok.com/v2/auth/authorize/") or "").strip()

    def _api_base_url(self) -> str:
        return (getattr(settings, "TIKTOK_API_BASE_URL", "https://open.tiktokapis.com/v2/") or "").strip()

    def _scopes(self) -> str:
        return (
            getattr(settings, "TIKTOK_SCOPES", "user.info.basic,video.list")
            or "user.info.basic,video.list"
        ).strip()

    def _validate_config(self):
        if not self._client_key() or not self._client_secret() or not self._redirect_uri():
            raise ValueError("TikTok OAuth config is incomplete. Please set TIKTOK_CLIENT_KEY/TIKTOK_CLIENT_SECRET/TIKTOK_REDIRECT_URI")

    def get_oauth_authorize_url(self, state: str):
        self._validate_config()
        query = urlencode(
            {
                "client_key": self._client_key(),
                "redirect_uri": self._redirect_uri(),
                "response_type": "code",
                "scope": self._scopes(),
                "state": state,
            }
        )
        return f"{self._auth_base_url()}?{query}"

    def exchange_code_for_token(self, code: str):
        self._validate_config()
        token_url = f"{self._api_base_url().rstrip('/')}/oauth/token/"
        resp = requests.post(
            token_url,
            data={
                "client_key": self._client_key(),
                "client_secret": self._client_secret(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri(),
            },
            timeout=10,
        )
        payload = resp.json() if resp.content else {}
        if resp.status_code >= 400 or payload.get("error"):
            raise ValueError(payload.get("error_description") or payload.get("message") or "TikTok token exchange failed")

        data = payload.get("data", payload)
        open_id = data.get("open_id") or data.get("openid") or "default"
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": int(data.get("expires_in", 7200)),
            "account_id": open_id,
        }

    def refresh_token(self, refresh_token: str):
        self._validate_config()
        token_url = f"{self._api_base_url().rstrip('/')}/oauth/token/"
        resp = requests.post(
            token_url,
            data={
                "client_key": self._client_key(),
                "client_secret": self._client_secret(),
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=10,
        )
        payload = resp.json() if resp.content else {}
        if resp.status_code >= 400 or payload.get("error"):
            raise ValueError(payload.get("error_description") or payload.get("message") or "TikTok refresh token failed")
        data = payload.get("data", payload)
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_in": int(data.get("expires_in", 7200)),
        }

    def fetch_order_list(self, access_token: str, page_size: int = 50, cursor: str = ""):
        self._validate_config()
        api_url = f"{self._api_base_url().rstrip('/')}/order/list/"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"page_size": max(1, min(int(page_size or 50), 100))}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(api_url, headers=headers, params=params, timeout=12)
        payload = resp.json() if resp.content else {}
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            raise PlatformRateLimitError("TikTok orderlist rate limited", retry_after=int(retry_after))
        if resp.status_code >= 400:
            raise ValueError(payload.get("message") or "TikTok orderlist failed")
        data = payload.get("data", payload)
        if payload.get("code") in {"rate_limited", "too_many_requests"}:
            retry_after = data.get("retry_after", 60)
            raise PlatformRateLimitError("TikTok orderlist rate limited", retry_after=int(retry_after))
        return {
            "orders": data.get("orders", []),
            "next_cursor": data.get("next_cursor") or "",
            "has_more": bool(data.get("has_more")),
        }
