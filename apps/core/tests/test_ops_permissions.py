from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.permissions import IsOpsAdmin


class IsOpsAdminUnitTest(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    @override_settings(OPS_ADMIN_USERNAMES=["ops_from_settings"])
    def test_ops_admin_by_settings(self):
        user = self.user_model.objects.create_user(username="ops_from_settings", password="pwd123456")
        request = type("Req", (), {"user": user})()
        self.assertTrue(IsOpsAdmin().has_permission(request, None))

    def test_ops_admin_by_group(self):
        user = self.user_model.objects.create_user(username="ops_from_group", password="pwd123456")
        group, _ = Group.objects.get_or_create(name="ops_admin")
        user.groups.add(group)
        request = type("Req", (), {"user": user})()
        self.assertTrue(IsOpsAdmin().has_permission(request, None))

    def test_non_ops_user_denied(self):
        user = self.user_model.objects.create_user(username="normal_user", password="pwd123456")
        request = type("Req", (), {"user": user})()
        self.assertFalse(IsOpsAdmin().has_permission(request, None))


class OpsEndpointsPermissionTest(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.client = APIClient()
        self.normal = self.user_model.objects.create_user(username="normal", password="pwd123456")
        self.ops = self.user_model.objects.create_user(username="ops_user", password="pwd123456")
        group, _ = Group.objects.get_or_create(name="ops_admin")
        self.ops.groups.add(group)

    def test_dead_letter_requires_ops_admin(self):
        self.client.force_authenticate(self.normal)
        denied = self.client.get("/api/ops/dead-letter/")
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.ops)
        allowed = self.client.get("/api/ops/dead-letter/")
        self.assertEqual(allowed.status_code, 200)

    @override_settings(OPS_ADMIN_USERNAMES=["ops_user"])
    def test_ops_whoami(self):
        self.client.force_authenticate(self.ops)
        resp = self.client.get("/api/ops/whoami/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["code"], 200)
        self.assertTrue(resp.data["data"]["is_ops_admin"])
