from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import AccountDeletionLog, UserPhoneBinding
from apps.core.sms_service import store_sms_code


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, SMS_PROVIDER_CHAIN=["mock"])
class MobileAuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = "/api/auth/mobile/login"
        self.delete_url = "/api/user/account/"
        self.full_phone = "+8613800138000"
        self.mobile = "13800138000"
        self.code = "123456"

    def test_login_requires_privacy_agreement(self):
        store_sms_code(self.full_phone, self.code)
        resp = self.client.post(
            self.login_url,
            {"mobile": self.mobile, "country_code": "86", "code": self.code, "agreed_privacy": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("隐私", resp.data["message"])

    def test_mobile_login_register_and_delete_account(self):
        store_sms_code(self.full_phone, self.code)
        login_resp = self.client.post(
            self.login_url,
            {"mobile": self.mobile, "country_code": "86", "code": self.code, "agreed_privacy": True},
            format="json",
            HTTP_X_DEVICE_ID="dev-001",
        )
        self.assertEqual(login_resp.status_code, 200)
        access = login_resp.data["data"]["access"]
        self.assertTrue(access)
        self.assertTrue(UserPhoneBinding.objects.filter(country_code="86", phone_number=self.mobile).exists())

        store_sms_code(self.full_phone, self.code)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        delete_resp = self.client.delete(self.delete_url, {"code": self.code, "reason": "test"}, format="json")
        self.assertEqual(delete_resp.status_code, 200)

        user = get_user_model().objects.get(id=login_resp.data["data"]["user"]["id"])
        self.assertFalse(user.is_active)
        self.assertTrue(AccountDeletionLog.objects.filter(user=user).exists())
