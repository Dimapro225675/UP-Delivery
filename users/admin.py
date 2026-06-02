from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .admin_permissions import RestrictedCreationMixin, has_full_admin_access
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(RestrictedCreationMixin, UserAdmin):
    list_display = ["username", "full_name", "email", "phone", "role", "is_staff"]
    list_filter = ["role", "is_staff", "is_active"]
    search_fields = ["username", "full_name", "email", "phone"]
    fieldsets = UserAdmin.fieldsets + (
        ("Профиль доставки", {"fields": ("full_name", "phone", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Профиль доставки", {"fields": ("full_name", "phone", "email", "role")}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if has_full_admin_access(request.user):
            return fieldsets

        normalized = []
        for title, options in fieldsets:
            fields = list(options.get("fields", ()))
            for restricted_field in ("is_staff", "is_superuser", "groups", "user_permissions"):
                if restricted_field in fields:
                    fields.remove(restricted_field)
            normalized.append((title, {**options, "fields": tuple(fields)}))
        return tuple(normalized)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not has_full_admin_access(request.user):
            for restricted_field in ("is_staff", "is_superuser", "groups", "user_permissions"):
                if restricted_field in form.base_fields:
                    form.base_fields.pop(restricted_field)
        return form

    def save_model(self, request, obj, form, change):
        obj.is_staff = obj.role in {CustomUser.ROLE_DISPATCHER, CustomUser.ROLE_ADMIN} or obj.is_superuser
        super().save_model(request, obj, form, change)


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass
