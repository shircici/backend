import time
from dataclasses import dataclass


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


def get_platform_client(platform: str) -> BasePlatformClient:
    supported = {"tiktok", "amazon", "1688"}
    if platform not in supported:
        raise ValueError(f"Unsupported platform: {platform}")
    return BasePlatformClient(platform=platform)
