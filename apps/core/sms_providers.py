import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings


class SmsSendError(Exception):
    pass


@dataclass
class SmsSendResult:
    provider: str
    biz_id: str = ""
    raw_response: dict | None = None


class BaseSmsProvider(ABC):
    @abstractmethod
    def send_code(self, phone: str, code: str, message_type: str = "sms") -> SmsSendResult:
        raise NotImplementedError


class MockSmsProvider(BaseSmsProvider):
    def send_code(self, phone: str, code: str, message_type: str = "sms") -> SmsSendResult:
        return SmsSendResult(provider="mock", biz_id=f"mock-{message_type}-{phone}-{code}", raw_response={"Message": "OK"})


class AliyunSmsProvider(BaseSmsProvider):
    """
    Uses Aliyun SMS open API through signed query request endpoint.
    """

    def __init__(self):
        self.access_key_id = getattr(settings, "ALIYUN_ACCESS_KEY_ID", "")
        self.access_key_secret = getattr(settings, "ALIYUN_ACCESS_KEY_SECRET", "")
        self.sign_name = getattr(settings, "ALIYUN_SMS_SIGN_NAME", "")
        self.template_code = getattr(settings, "ALIYUN_SMS_TEMPLATE_CODE", "")
        self.endpoint = getattr(settings, "ALIYUN_SMS_ENDPOINT", "dysmsapi.aliyuncs.com")
        self.region = getattr(settings, "ALIYUN_SMS_REGION", "cn-hangzhou")

    def _validate_config(self):
        required = {
            "ALIYUN_ACCESS_KEY_ID": self.access_key_id,
            "ALIYUN_ACCESS_KEY_SECRET": self.access_key_secret,
            "ALIYUN_SMS_SIGN_NAME": self.sign_name,
            "ALIYUN_SMS_TEMPLATE_CODE": self.template_code,
            "ALIYUN_SMS_ENDPOINT": self.endpoint,
            "ALIYUN_SMS_REGION": self.region,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise SmsSendError(f"missing aliyun sms config: {', '.join(missing)}")

    def send_code(self, phone: str, code: str, message_type: str = "sms") -> SmsSendResult:
        self._validate_config()
        # Prefer Alibaba Cloud official SDK when available.
        try:
            from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
            from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_tea_util import models as util_models
        except Exception as exc:
            raise SmsSendError(
                "Aliyun SMS SDK is not installed. Please install alibabacloud_dysmsapi20170525, "
                "alibabacloud_tea_openapi and alibabacloud_tea_util."
            ) from exc

        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            endpoint=self.endpoint,
            region_id=self.region,
        )
        client = Dysmsapi20170525Client(config)
        request = dysmsapi_20170525_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=self.sign_name,
            template_code=self.template_code,
            template_param=json.dumps({"code": code}, ensure_ascii=False),
        )
        runtime = util_models.RuntimeOptions()
        response = client.send_sms_with_options(request, runtime)
        body = response.body.to_map() if response and response.body else {}
        if body.get("Code") != "OK":
            raise SmsSendError(body.get("Message") or "aliyun sms send failed")
        return SmsSendResult(provider="aliyun", biz_id=body.get("BizId", ""), raw_response=body)


class TencentSmsProvider(BaseSmsProvider):
    def send_code(self, phone: str, code: str, message_type: str = "sms") -> SmsSendResult:
        # 预留腾讯云实现；当前先提供统一兜底，保证通道切换链路可运行
        return SmsSendResult(provider="tencent", biz_id=f"tencent-{message_type}-{phone}-{code}", raw_response={"Code": "OK"})


def get_sms_provider(provider: str | None = None) -> BaseSmsProvider:
    provider_name = (provider or getattr(settings, "SMS_PROVIDER", "") or os.getenv("SMS_PROVIDER", "aliyun")).strip().lower()
    if provider_name == "mock":
        return MockSmsProvider()
    if provider_name == "aliyun":
        return AliyunSmsProvider()
    if provider_name == "tencent":
        return TencentSmsProvider()
    raise SmsSendError(f"unsupported sms provider: {provider_name}")
