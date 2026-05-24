from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "full_name", "email", "phone", "role", "is_staff"]
    list_filter = ["role", "is_staff", "is_active"]
    search_fields = ["username", "full_name", "email", "phone"]
    fieldsets = UserAdmin.fieldsets + (
        ("Профиль доставки", {"fields": ("full_name", "phone", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Профиль доставки", {"fields": ("full_name", "phone", "email", "role")}),
    )

    def has_module_permission(self, request):
        return request.user.is_superuser or getattr(request.user, "role", "") == CustomUser.ROLE_ADMIN

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)
