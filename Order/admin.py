import json

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html

from users.admin_permissions import AdminWorkspaceMixin

from .models import (
    AuditLog,
    DeliveryReportPhoto,
    DeliveryType,
    Issue,
    Order,
    OrderPhoto,
    StatusHistory,
)


class MultipleAdminFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ClientAlphabetFilter(admin.SimpleListFilter):
    title = "Клиент (алфавит)"
    parameter_name = "client_initial"

    def lookups(self, request, model_admin):
        return [(letter, letter.upper()) for letter in "abcdefghijklmnopqrstuvwxyz"]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(client__username__istartswith=self.value())
        return queryset


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ["timestamp"]
    fields = ["status", "comment", "location", "courier", "timestamp"]


class IssueInline(admin.TabularInline):
    model = Issue
    extra = 0
    fields = ["issue_type", "description", "resolved", "resolved_at"]


class OrderPhotoInline(admin.TabularInline):
    model = OrderPhoto
    extra = 1
    fields = ["image", "created_at"]
    readonly_fields = ["created_at"]


class DeliveryReportPhotoInline(admin.TabularInline):
    model = DeliveryReportPhoto
    extra = 1
    fields = ["image", "created_at"]
    readonly_fields = ["created_at"]


class OrderAdminForm(forms.ModelForm):
    order_photos_upload = forms.FileField(
        label="Фотографии заказа",
        required=False,
        widget=MultipleAdminFileInput(attrs={"accept": "image/*"}),
        help_text="Можно выбрать сразу несколько фотографий заказа.",
    )
    delivery_report_photos_upload = forms.FileField(
        label="Фотографии доставки",
        required=False,
        widget=MultipleAdminFileInput(attrs={"accept": "image/*"}),
        help_text="Можно выбрать сразу несколько фотографий для фотоотчета.",
    )

    class Meta:
        model = Order
        fields = "__all__"

    class Media:
        js = ("admin/js/order_admin.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["courier"].queryset = user_model.objects.filter(role=user_model.ROLE_COURIER).order_by("username")

        self.fields["distance_km"].disabled = True
        self.fields["delivery_price"].disabled = True
        self.fields["distance_km"].help_text = "Рассчитывается автоматически по выбранным городам."
        self.fields["delivery_price"].help_text = "Рассчитывается автоматически по типу доставки, маршруту и габаритам."

        delivery_types = [
            {
                "id": delivery_type.id,
                "name": delivery_type.name,
                "base_price": float(delivery_type.base_price),
                "max_distance": delivery_type.max_distance,
            }
            for delivery_type in DeliveryType.objects.order_by("name")
        ]
        city_distances = {",".join(sorted(key)): value for key, value in Order.CITY_DISTANCES_KM.items()}
        pricing_config = {
            "included_weight_kg": float(Order.INCLUDED_WEIGHT_KG),
            "included_side_cm": float(Order.INCLUDED_SIDE_CM),
            "address_delivery_surcharge": float(Order.ADDRESS_DELIVERY_SURCHARGE),
            "overweight_price_per_kg": float(Order.OVERWEIGHT_PRICE_PER_KG),
            "oversize_price_per_10_cm": float(Order.OVERSIZE_PRICE_PER_10_CM),
            "intercity_price_per_10_km": float(Order.INTERCITY_PRICE_PER_10_KM),
            "city_distances_km": city_distances,
        }

        self.delivery_types_data = delivery_types
        self.city_distances_data = city_distances
        self.pricing_config_data = pricing_config

        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["distance_km"].initial = instance.calculate_distance_km()
            self.fields["delivery_price"].initial = instance.calculate_delivery_price()


@admin.register(Order)
class OrderAdmin(AdminWorkspaceMixin, admin.ModelAdmin):
    change_form_template = "admin/Order/order/change_form.html"

    class Media:
        js = ("admin/js/order_admin.js",)

    form = OrderAdminForm
    list_display = ["tracking_number", "status_badge", "client_link", "courier_link", "delivery_price", "created_at"]
    list_filter = ["status", ClientAlphabetFilter, "delivery_type", "created_at"]
    search_fields = ["tracking_number", "pickup_address", "delivery_address", "client__username", "courier__username"]
    date_hierarchy = "created_at"
    readonly_fields = ["tracking_number", "created_at", "updated_at", "delivered_at"]
    inlines = [OrderPhotoInline, DeliveryReportPhotoInline, StatusHistoryInline, IssueInline]
    ordering = ["status", "client__username", "tracking_number"]

    fieldsets = (
        ("Основная информация", {"fields": ("tracking_number", "client", "courier", "status", "delivery_type")}),
        ("Маршрут", {"fields": ("pickup_city", "pickup_street", "pickup_house", "delivery_to_pickup_point", "delivery_city", "delivery_street", "delivery_house", "distance_km")}),
        ("Груз", {"fields": ("weight_kg", "length_cm", "width_cm", "height_cm")}),
        ("Стоимость", {"fields": ("delivery_price",)}),
        ("Фотографии", {"fields": ("order_photos_upload", "delivery_report_photos_upload")}),
        ("Вручение", {"fields": ("delivered_at", "client_confirmed_at")}),
        ("Служебное", {"fields": ("description", "created_at", "updated_at")}),
    )

    def render_change_form(self, request, context, *args, **kwargs):
        admin_form = context.get("adminform")
        form = getattr(admin_form, "form", None)
        if form:
            context["order_admin_delivery_types_json"] = getattr(form, "delivery_types_data", [])
            context["order_admin_city_distances_json"] = getattr(form, "city_distances_data", {})
            context["order_admin_pricing_config_json"] = getattr(form, "pricing_config_data", {})
        return super().render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.courier_id:
            if obj.status == Order.STATUS_WAITING:
                obj.status = Order.STATUS_WAITING_COURIER
        elif obj.status == Order.STATUS_WAITING_COURIER:
            obj.status = Order.STATUS_WAITING
        super().save_model(request, obj, form, change)

        for image in request.FILES.getlist("order_photos_upload"):
            OrderPhoto.objects.create(order=obj, image=image)
        for image in request.FILES.getlist("delivery_report_photos_upload"):
            DeliveryReportPhoto.objects.create(order=obj, image=image)

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
class DeliveryTypeAdmin(AdminWorkspaceMixin, admin.ModelAdmin):
    list_display = ["name", "max_distance", "base_price"]
    search_fields = ["name"]


@admin.register(Issue)
class IssueAdmin(AdminWorkspaceMixin, admin.ModelAdmin):
    list_display = ["order", "issue_type", "resolved", "created_by", "created_at"]
    list_filter = ["issue_type", "resolved"]
    search_fields = ["description", "order__tracking_number"]


@admin.register(StatusHistory)
class StatusHistoryAdmin(AdminWorkspaceMixin, admin.ModelAdmin):
    list_display = ["order", "status", "courier", "location", "timestamp"]
    list_filter = ["status", "timestamp"]
    search_fields = ["order__tracking_number", "comment", "location"]


@admin.register(AuditLog)
class AuditLogAdmin(AdminWorkspaceMixin, admin.ModelAdmin):
    list_display = ["created_at", "user", "order", "action"]
    list_filter = ["action", "created_at"]
    search_fields = ["order__tracking_number", "details", "user__username"]
    readonly_fields = ["created_at"]
