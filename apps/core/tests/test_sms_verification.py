from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class SmsVerificationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.send_url = "/api/auth/sms/send-code"
        self.verify_url = "/api/auth/sms/verify-code"
        self.phone = "13800138000"

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, SMS_PROVIDER_CHAIN=["mock"])
    def test_send_and_verify_success(self):
        send_resp = self.client.post(self.send_url, {"phone": self.phone}, format="json")
        self.assertEqual(send_resp.status_code, 200)
        self.assertEqual(send_resp.data["data"]["provider"], "mock")
        code = send_resp.data["data"]["code"]
        full_phone = send_resp.data["data"]["phone"]
        self.assertRegex(code, r"^\d{4,6}$")

        verify_resp = self.client.post(
            self.verify_url,
            {"phone": full_phone, "code": code},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertTrue(verify_resp.data["data"]["verified"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, SMS_PROVIDER_CHAIN=["mock"])
    def test_verify_should_fail_with_wrong_code(self):
        send_resp = self.client.post(self.send_url, {"phone": self.phone}, format="json")
        full_phone = send_resp.data["data"]["phone"]
        verify_resp = self.client.post(
            self.verify_url,
            {"phone": full_phone, "code": "000000"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, 400)
        self.assertIn("invalid or expired verification code", verify_resp.data["message"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, SMS_PROVIDER_CHAIN=["mock"])
    def test_verify_code_is_one_time(self):
        send_resp = self.client.post(self.send_url, {"phone": self.phone}, format="json")
        code = send_resp.data["data"]["code"]
        full_phone = send_resp.data["data"]["phone"]

        first_verify = self.client.post(self.verify_url, {"phone": full_phone, "code": code}, format="json")
        second_verify = self.client.post(self.verify_url, {"phone": full_phone, "code": code}, format="json")
        self.assertEqual(first_verify.status_code, 200)
        self.assertEqual(second_verify.status_code, 400)

    @override_settings(SMS_SEND_MIN_INTERVAL_SECONDS=60)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, SMS_PROVIDER_CHAIN=["mock"])
    def test_send_rate_limited_within_cooldown(self):
        first = self.client.post(self.send_url, {"phone": self.phone}, format="json")
        self.assertEqual(first.status_code, 200)
        second = self.client.post(self.send_url, {"phone": self.phone}, format="json")
        self.assertEqual(second.status_code, 429)
        self.assertIn("频繁", second.data["message"])

    @override_settings(SMS_VERIFY_MAX_FAILURES=3)
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, SMS_PROVIDER_CHAIN=["mock"])
    def test_verify_locked_after_max_failures(self):
        send_resp = self.client.post(self.send_url, {"phone": self.phone}, format="json")
        full_phone = send_resp.data["data"]["phone"]

        for _ in range(2):
            r = self.client.post(self.verify_url, {"phone": full_phone, "code": "000000"}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn("invalid or expired verification code", r.data["message"])

        locked = self.client.post(self.verify_url, {"phone": full_phone, "code": "000000"}, format="json")
        self.assertEqual(locked.status_code, 429)
        self.assertIn("验证尝试过多", locked.data["message"])

        still_locked = self.client.post(self.verify_url, {"phone": full_phone, "code": "000000"}, format="json")
        self.assertEqual(still_locked.status_code, 429)
