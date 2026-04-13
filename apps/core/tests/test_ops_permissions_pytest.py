import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.core.permissions import IsOpsAdmin


@pytest.mark.django_db
def test_is_ops_admin_by_group():
    user_model = get_user_model()
    user = user_model.objects.create_user(username="ops_pytest", password="pwd123456")
    group, _ = Group.objects.get_or_create(name="ops_admin")
    user.groups.add(group)
    request = type("Req", (), {"user": user})()
    assert IsOpsAdmin().has_permission(request, None) is True


@pytest.mark.django_db
def test_dead_letter_endpoint_permission():
    user_model = get_user_model()
    normal = user_model.objects.create_user(username="normal_pytest", password="pwd123456")
    ops = user_model.objects.create_user(username="ops_pytest_2", password="pwd123456")
    group, _ = Group.objects.get_or_create(name="ops_admin")
    ops.groups.add(group)

    client = APIClient()
    client.force_authenticate(normal)
    denied = client.get("/api/ops/dead-letter/")
    assert denied.status_code == 403

    client.force_authenticate(ops)
    allowed = client.get("/api/ops/dead-letter/")
    assert allowed.status_code == 200
