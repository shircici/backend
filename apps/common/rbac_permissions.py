from django.conf import settings
from rest_framework.permissions import BasePermission


class HasApiIntegratorRole(BasePermission):
    """
    RBAC：业务集成角色（Django Group）。
    - 生产建议设置 RBAC_ENFORCE=true，并为用户分配 Group（默认名 api_integrator）。
    - RBAC_ENFORCE=false 时：仅需已登录即可（便于联调）；超级用户始终放行。
    """

    message = "需要业务集成角色（Django Group）或超级管理员"

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        if not getattr(settings, "RBAC_ENFORCE", False):
            return True
        groups = getattr(settings, "RBAC_API_INTEGRATOR_GROUPS", ["api_integrator"])
        return user.groups.filter(name__in=groups).exists()
