from django.conf import settings
from rest_framework.permissions import BasePermission


class CanAccessSelectionEngine(BasePermission):
    """
    选品决策算法引擎：需具备「选品决策员」或「管理层」Django Group。
    RBAC_ENFORCE=false 时：已登录即可（便于联调）；超级用户始终放行。
    """

    message = "需要选品决策员或管理层角色"

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        if not getattr(settings, "RBAC_ENFORCE", False):
            return True
        groups = getattr(
            settings,
            "RBAC_SELECTION_ENGINE_GROUPS",
            ["selection_decision_maker", "management"],
        )
        return user.groups.filter(name__in=groups).exists()
