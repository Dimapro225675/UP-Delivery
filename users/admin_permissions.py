from .models import CustomUser


def has_admin_workspace_access(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", "") in {CustomUser.ROLE_DISPATCHER, CustomUser.ROLE_ADMIN}
        )
    )


def has_full_admin_access(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and (getattr(user, "is_superuser", False) or getattr(user, "role", "") == CustomUser.ROLE_ADMIN)
    )


class AdminWorkspaceMixin:
    def has_module_permission(self, request):
        return has_admin_workspace_access(request.user)

    def has_view_permission(self, request, obj=None):
        return has_admin_workspace_access(request.user)

    def has_add_permission(self, request):
        return has_admin_workspace_access(request.user)

    def has_change_permission(self, request, obj=None):
        return has_admin_workspace_access(request.user)

    def has_delete_permission(self, request, obj=None):
        return has_admin_workspace_access(request.user)


class RestrictedCreationMixin(AdminWorkspaceMixin):
    def has_add_permission(self, request):
        return has_full_admin_access(request.user)
