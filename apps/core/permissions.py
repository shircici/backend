from django.conf import settings
from rest_framework.permissions import BasePermission


class IsOpsAdmin(BasePermission):
    """
    Ops access switch independent of is_staff.
    Priority:
    1) superuser always allowed
    2) username in settings.OPS_ADMIN_USERNAMES
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.groups.filter(name="ops_admin").exists():
            return True
        ops_users = set(getattr(settings, "OPS_ADMIN_USERNAMES", []))
        return user.username in ops_users


class HasOrderEditPermission(BasePermission):
    """
    订单手动改地址权限：
    - 超级管理员放行
    - 其他用户需具备 core.order_edit 权限
    """

    message = "缺少订单编辑权限（order_edit）"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.has_perm("core.order_edit")
