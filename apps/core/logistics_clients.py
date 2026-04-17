from dataclasses import dataclass
from decimal import Decimal

import requests
from django.conf import settings


def _safe_iso_date(value):
    if not value:
        return ""
    value = str(value)
    if "T" in value:
        return value.split("T", 1)[0]
    return value[:10]


@dataclass
class LogisticsAggregatorClient:
    """
    物流聚合层抽象，默认优先 17Track，其次快递100。
    输出统一轨迹格式：
    [{"time":"2026-04-16","status":"已揽收","location":"深圳"}]
    """

    provider: str

    def fetch_tracking_events(self, waybill_no: str, carrier: str = ""):
        provider = (self.provider or "").lower().strip()
        if provider == "kuaidi100":
            return self._fetch_kuaidi100_events(waybill_no=waybill_no, carrier=carrier)
        return self._fetch_17track_events(waybill_no=waybill_no, carrier=carrier)

    def estimate_quotes(self, chargeable_weight_kg: Decimal, destination_country: str, carrier: str = ""):
        provider = (self.provider or "").lower().strip()
        if provider == "kuaidi100":
            return self._estimate_kuaidi100_quotes(chargeable_weight_kg, destination_country, carrier)
        return self._estimate_17track_quotes(chargeable_weight_kg, destination_country, carrier)

    def _fetch_17track_events(self, waybill_no: str, carrier: str = ""):
        api_key = (getattr(settings, "TRACK17_API_KEY", "") or "").strip()
        endpoint = (getattr(settings, "TRACK17_API_BASE_URL", "https://api.17track.net/track/v2") or "").strip().rstrip("/")
        if not api_key:
            return []
        resp = requests.post(
            f"{endpoint}/gettrackinfo",
            headers={"17token": api_key, "Content-Type": "application/json"},
            json={"data": [{"number": waybill_no, "carrier": carrier or None}]},
            timeout=10,
        )
        payload = resp.json() if resp.content else {}
        data = (payload.get("data") or [{}])[0]
        tracks = data.get("track_info", {}).get("tracking") or []
        return [
            {
                "time": _safe_iso_date(item.get("track_date") or item.get("time")),
                "status": item.get("status_description") or item.get("description") or "",
                "location": item.get("location") or "",
            }
            for item in tracks
        ]

    def _fetch_kuaidi100_events(self, waybill_no: str, carrier: str = ""):
        api_key = (getattr(settings, "KUAIDI100_API_KEY", "") or "").strip()
        endpoint = (getattr(settings, "KUAIDI100_TRACK_URL", "https://poll.kuaidi100.com/poll/query.do") or "").strip()
        if not api_key:
            return []
        resp = requests.get(
            endpoint,
            params={"num": waybill_no, "com": carrier, "key": api_key},
            timeout=10,
        )
        payload = resp.json() if resp.content else {}
        traces = payload.get("data") or []
        return [
            {
                "time": _safe_iso_date(item.get("ftime") or item.get("time")),
                "status": item.get("context") or "",
                "location": item.get("areaCode") or item.get("location") or "",
            }
            for item in traces
        ]

    def _estimate_17track_quotes(self, chargeable_weight_kg: Decimal, destination_country: str, carrier: str = ""):
        # 17Track 实时运价接口在企业版能力差异较大，这里保留统一返回结构，便于后续替换真实调用。
        if carrier:
            return [
                {
                    "carrier": carrier,
                    "destination_country": destination_country,
                    "currency": "CNY",
                    "estimated_price": None,
                    "source": "17track",
                    "note": "待接入企业版实时价格接口",
                }
            ]
        return []

    def _estimate_kuaidi100_quotes(self, chargeable_weight_kg: Decimal, destination_country: str, carrier: str = ""):
        # 快递100不同版本价格接口字段不同；先统一结构，后续替换真实解析。
        if carrier:
            return [
                {
                    "carrier": carrier,
                    "destination_country": destination_country,
                    "currency": "CNY",
                    "estimated_price": None,
                    "source": "kuaidi100",
                    "note": "待接入快递100实时价格接口",
                }
            ]
        return []


def get_logistics_aggregator_client() -> LogisticsAggregatorClient:
    provider = getattr(settings, "LOGISTICS_AGGREGATOR_PROVIDER", "17track")
    return LogisticsAggregatorClient(provider=provider)
