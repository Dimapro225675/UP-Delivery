from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class DeliveryType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    max_distance = models.PositiveIntegerField(
        help_text="Максимальное расстояние в км",
        verbose_name="Макс. расстояние"
    )
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Базовая цена"
    )

    class Meta:
        verbose_name = "Тип доставки"
        verbose_name_plural = "Типы доставки"

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('assigned', 'Назначен курьеру'),
        ('in_progress', 'В доставке'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='client_orders',
        verbose_name="Клиент"
    )
    courier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courier_orders',
        verbose_name="Курьер"
    )
    pickup_address = models.TextField(verbose_name="Адрес pickup")
    delivery_address = models.TextField(verbose_name="Адрес доставки")
    description = models.TextField(blank=True, verbose_name="Описание")
    delivery_type = models.ForeignKey(
        DeliveryType,
        on_delete=models.PROTECT,
        verbose_name="Тип доставки"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.pk} - {self.status}"


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('paid', 'Оплачен'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возвращен'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Заказ"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, verbose_name="Способ оплаты")
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    transaction_id = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"

    def __str__(self):
        return f"Платеж {self.amount}р за заказ #{self.order.pk}"


class StatusHistory(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('assigned', 'Назначен курьеру'),
        ('picked_up', 'Забран'),
        ('in_transit', 'В пути'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="Заказ"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    courier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Курьер"
    )
    comment = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "История статуса"
        verbose_name_plural = "История статусов"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.order.pk}: {self.status} в {self.timestamp}"


class Issue(models.Model):
    ISSUE_TYPES = [
        ('delay', 'Задержка'),
        ('damage', 'Повреждение'),
        ('wrong_address', 'Неверный адрес'),
        ('payment_issue', 'Проблема с оплатой'),
        ('other', 'Другое'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='issues',
        verbose_name="Заказ"
    )
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    description = models.TextField(verbose_name="Описание")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Создал"
    )
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Проблема"
        verbose_name_plural = "Проблемы"

    def __str__(self):
        return f"Проблема {self.issue_type} для заказа #{self.order.pk}"
