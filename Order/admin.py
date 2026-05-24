from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import AuditLog, DeliveryType, Issue, Order, StatusHistory


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ["timestamp"]
    fields = ["status", "comment", "location", "courier", "timestamp"]


class IssueInline(admin.TabularInline):
    model = Issue
    extra = 0
    fields = ["issue_type", "description", "resolved", "resolved_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["tracking_number", "status_badge", "client_link", "courier_link", "delivery_price", "created_at"]
    list_filter = ["status", "delivery_type", "created_at"]
    search_fields = ["tracking_number", "pickup_address", "delivery_address", "client__username", "courier__username"]
    date_hierarchy = "created_at"
    readonly_fields = ["tracking_number", "delivery_price", "created_at", "updated_at", "delivered_at"]
    inlines = [StatusHistoryInline, IssueInline]

    fieldsets = (
        ("Основная информация", {"fields": ("tracking_number", "client", "courier", "status", "delivery_type")}),
        ("Маршрут", {"fields": ("pickup_city", "pickup_street", "pickup_house", "delivery_to_pickup_point", "delivery_city", "delivery_street", "delivery_house", "distance_km")}),
        ("Груз", {"fields": ("weight_kg", "length_cm", "width_cm", "height_cm", "order_photo")}),
        ("Стоимость", {"fields": ("delivery_price",)}),
        ("Вручение", {"fields": ("delivery_attempts", "max_delivery_attempts", "delivery_report_photo", "delivered_at", "client_confirmed_at")}),
        ("Служебное", {"fields": ("description", "created_at", "updated_at")}),
    )

    def status_badge(self, obj):
        badge_class = {
            Order.STATUS_WAITING: "secondary",
            Order.STATUS_WAITING_COURIER: "info",
            Order.STATUS_DELIVERING: "warning",
            Order.STATUS_DELIVERED_PICKUP_POINT: "success",
            Order.STATUS_DELIVERED_ADDRESS: "success",
            Order.STATUS_CONFIRMED: "primary",
            Order.STATUS_RETURNED: "danger",
            Order.STATUS_CANCELLED: "dark",
        }.get(obj.status, "secondary")
        return format_html('<span class="badge bg-{}">{}</span>', badge_class, obj.get_status_display())

    status_badge.short_description = "Статус"

    def client_link(self, obj):
        url = reverse("admin:users_customuser_change", args=[obj.client.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client)

    client_link.short_description = "Клиент"

    def courier_link(self, obj):
        if not obj.courier:
            return "-"
        url = reverse("admin:users_customuser_change", args=[obj.courier.pk])
        return format_html('<a href="{}">{}</a>', url, obj.courier)

    courier_link.short_description = "Курьер"


@admin.register(DeliveryType)
class DeliveryTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "max_distance", "base_price", "price_per_kg", "price_per_m3", "urgency_multiplier"]
    search_fields = ["name"]

    def has_module_permission(self, request):
        return request.user.is_superuser or getattr(request.user, "role", "") in {"dispatcher", "admin"}

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["order", "issue_type", "resolved", "created_by", "created_at"]
    list_filter = ["issue_type", "resolved"]
    search_fields = ["description", "order__tracking_number"]


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "courier", "location", "timestamp"]
    list_filter = ["status", "timestamp"]
    search_fields = ["order__tracking_number", "comment", "location"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "order", "action"]
    list_filter = ["action", "created_at"]
    search_fields = ["order__tracking_number", "details", "user__username"]
    readonly_fields = ["created_at"]
