from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, Payment, StatusHistory, Issue, DeliveryType


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['amount', 'payment_method', 'status', 'transaction_id', 'paid_at']


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ['timestamp', 'status_display']
    fields = ['status', 'comment', 'location', 'courier', 'timestamp']

    def status_display(self, obj):
        return obj.get_status_display()

    status_display.short_description = 'Статус'


class IssueInline(admin.TabularInline):
    model = Issue
    extra = 1
    fields = ['issue_type', 'description', 'resolved', 'resolved_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['pk', 'status_badge', 'client_link', 'courier_link',
                    'delivery_address_short', 'delivery_type', 'created_at']
    list_filter = ['status', 'delivery_type', 'created_at']
    search_fields = ['pickup_address', 'delivery_address', 'pk']
    date_hierarchy = 'created_at'
    inlines = [PaymentInline, StatusHistoryInline, IssueInline]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('client', 'courier', 'status', 'delivery_type')
        }),
        ('Адреса', {
            'fields': ('pickup_address', 'delivery_address')
        }),
        ('Детали', {
            'fields': ('description', 'created_at', 'updated_at')
        }),
    )

    def status_badge(self, obj):
        badge_class = {
            'new': 'secondary', 'assigned': 'info', 'in_progress': 'warning',
            'delivered': 'success', 'cancelled': 'danger'
        }.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}-subtle text-{} border border-{}">{} ({})</span>',
            badge_class, badge_class, badge_class, obj.get_status_display(), obj.status
        )

    status_badge.short_description = 'Статус'

    def client_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.client.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client.username)

    client_link.short_description = 'Клиент'

    def courier_link(self, obj):
        if obj.courier:
            url = reverse('admin:auth_user_change', args=[obj.courier.pk])
            return format_html('<a href="{}">{}</a>', url, obj.courier.username)
        return '-'

    courier_link.short_description = 'Курьер'

    def delivery_address_short(self, obj):
        return obj.delivery_address[:50] + '...' if len(obj.delivery_address) > 50 else obj.delivery_address

    delivery_address_short.short_description = 'Адрес доставки'


@admin.register(DeliveryType)
class DeliveryTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_distance', 'base_price']
    list_filter = ['max_distance']
    search_fields = ['name']
    fields = ['name', 'description', 'max_distance', 'base_price']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order_link', 'amount', 'payment_method', 'status_badge', 'paid_at']
    list_filter = ['status', 'payment_method', 'paid_at']
    search_fields = ['transaction_id', 'order__pk']

    def order_link(self, obj):
        url = reverse('admin:delivery_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">Заказ #{} </a>', url, obj.order.pk)

    order_link.short_description = 'Заказ'

    def status_badge(self, obj):
        badge_class = 'success' if obj.status == 'paid' else 'warning' if obj.status == 'pending' else 'danger'
        return format_html('<span class="badge bg-{}-subtle text-{}">{} ({})</span>',
                           badge_class, badge_class, obj.get_status_display(), obj.status)

    status_badge.short_description = 'Статус'


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['order_link', 'issue_type', 'resolved_badge', 'created_by']
    list_filter = ['issue_type', 'resolved']
    search_fields = ['description', 'order__pk']

    def order_link(self, obj):
        url = reverse('admin:delivery_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">Заказ #{} </a>', url, obj.order.pk)

    order_link.short_description = 'Заказ'

    def resolved_badge(self, obj):
        return format_html('<span class="badge bg-{}">{}</span>',
                           'success' if obj.resolved else 'danger',
                           'Решена' if obj.resolved else 'Открыта')

    resolved_badge.short_description = 'Статус'