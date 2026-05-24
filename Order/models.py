from decimal import Decimal, ROUND_CEILING
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class DeliveryType(models.Model):
    name = models.CharField("Название", max_length=100)
    description = models.TextField("Описание", blank=True)
    max_distance = models.PositiveIntegerField("Макс. расстояние", help_text="Максимальное расстояние в км")
    base_price = models.DecimalField("Базовая цена", max_digits=10, decimal_places=2)
    price_per_kg = models.DecimalField("Цена за кг", max_digits=10, decimal_places=2, default=Decimal("30.00"))
    price_per_m3 = models.DecimalField("Цена за м3", max_digits=10, decimal_places=2, default=Decimal("500.00"))
    declared_value_percent = models.DecimalField("Процент от ценности", max_digits=5, decimal_places=2, default=Decimal("1.00"))
    urgency_multiplier = models.DecimalField("Коэффициент срочности", max_digits=5, decimal_places=2, default=Decimal("1.00"))

    class Meta:
        verbose_name = "Тип доставки"
        verbose_name_plural = "Типы доставки"

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_WAITING = "waiting"
    STATUS_WAITING_COURIER = "waiting_courier"
    STATUS_DELIVERING = "delivering"
    STATUS_DELIVERED_PICKUP_POINT = "delivered_pickup_point"
    STATUS_DELIVERED_ADDRESS = "delivered_address"
    STATUS_CONFIRMED = "confirmed"
    STATUS_RETURNED = "returned"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_WAITING, "В ожидание"),
        (STATUS_WAITING_COURIER, "В ожидание курьера"),
        (STATUS_DELIVERING, "Доставляется"),
        (STATUS_DELIVERED_PICKUP_POINT, "Доставлен на пункт выдачи"),
        (STATUS_DELIVERED_ADDRESS, "Доставлен на адрес доставки"),
        (STATUS_CONFIRMED, "Подтвержден клиентом"),
        (STATUS_RETURNED, "Возврат"),
        (STATUS_CANCELLED, "Отменено"),
    ]
    STATUS_FLOW = {
        STATUS_WAITING: {STATUS_WAITING_COURIER, STATUS_CANCELLED},
        STATUS_WAITING_COURIER: {STATUS_DELIVERING, STATUS_CANCELLED, STATUS_RETURNED},
        STATUS_DELIVERING: {STATUS_DELIVERED_PICKUP_POINT, STATUS_DELIVERED_ADDRESS, STATUS_RETURNED},
        STATUS_DELIVERED_PICKUP_POINT: {STATUS_CONFIRMED},
        STATUS_DELIVERED_ADDRESS: {STATUS_CONFIRMED},
        STATUS_CONFIRMED: set(),
        STATUS_RETURNED: set(),
        STATUS_CANCELLED: set(),
    }

    CITY_CHOICES = [
        ("moscow", "Москва"),
        ("spb", "Санкт-Петербург"),
        ("kazan", "Казань"),
        ("nizhny", "Нижний Новгород"),
        ("ekb", "Екатеринбург"),
    ]
    CITY_DISTANCES_KM = {
        frozenset(("moscow", "spb")): 710,
        frozenset(("moscow", "kazan")): 820,
        frozenset(("moscow", "nizhny")): 420,
        frozenset(("moscow", "ekb")): 1800,
        frozenset(("spb", "kazan")): 1500,
        frozenset(("spb", "nizhny")): 1100,
        frozenset(("spb", "ekb")): 2300,
        frozenset(("kazan", "nizhny")): 390,
        frozenset(("kazan", "ekb")): 950,
        frozenset(("nizhny", "ekb")): 1300,
    }

    CARGO_DOCUMENTS = "documents"
    CARGO_PARCEL = "parcel"
    CARGO_FRAGILE = "fragile"
    CARGO_FOOD = "food"
    CARGO_OTHER = "other"
    CARGO_TYPES = [
        (CARGO_DOCUMENTS, "Документы"),
        (CARGO_PARCEL, "Посылка"),
        (CARGO_FRAGILE, "Хрупкий груз"),
        (CARGO_FOOD, "Продукты"),
        (CARGO_OTHER, "Другое"),
    ]
    FORBIDDEN_CARGO_TYPES = {"weapons", "animals", "hazardous"}

    CONFIRM_SIGNATURE = "signature"
    CONFIRM_PHOTO = "photo"
    CONFIRM_CODE = "code"
    CONFIRMATION_CHOICES = [
        (CONFIRM_SIGNATURE, "Электронная подпись"),
        (CONFIRM_PHOTO, "Фотоотчет"),
        (CONFIRM_CODE, "Код подтверждения"),
    ]

    INCLUDED_WEIGHT_KG = Decimal("50.00")
    INCLUDED_SIDE_CM = Decimal("100.00")
    ADDRESS_DELIVERY_SURCHARGE = Decimal("200.00")
    OVERWEIGHT_PRICE_PER_KG = Decimal("10.00")
    OVERSIZE_PRICE_PER_10_CM = Decimal("10.00")
    INTERCITY_PRICE_PER_10_KM = Decimal("100.00")

    tracking_number = models.CharField("Трекинг-номер", max_length=24, unique=True, editable=False)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_orders",
        verbose_name="Клиент",
    )
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courier_orders",
        verbose_name="Курьер",
    )
    pickup_city = models.CharField("Город забора", max_length=40, choices=CITY_CHOICES, default="moscow")
    pickup_street = models.CharField("Улица забора", max_length=150, default="")
    pickup_house = models.CharField("Дом забора", max_length=20, default="")
    delivery_to_pickup_point = models.BooleanField("Доставка на пункт выдачи", default=False)
    delivery_city = models.CharField("Город доставки", max_length=40, choices=CITY_CHOICES, default="moscow")
    delivery_street = models.CharField("Улица доставки", max_length=150, blank=True, default="")
    delivery_house = models.CharField("Дом доставки", max_length=20, blank=True, default="")
    pickup_address = models.TextField("Адрес забора", blank=True, default="")
    delivery_address = models.TextField("Адрес доставки", blank=True, default="")
    distance_km = models.PositiveIntegerField("Расстояние, км", default=1)
    description = models.TextField("Комментарий", blank=True)
    delivery_type = models.ForeignKey(DeliveryType, on_delete=models.PROTECT, verbose_name="Тип доставки")
    cargo_type = models.CharField("Тип отправления", max_length=30, choices=CARGO_TYPES, default=CARGO_PARCEL)
    weight_kg = models.DecimalField("Вес, кг", max_digits=7, decimal_places=2)
    length_cm = models.DecimalField("Длина, см", max_digits=7, decimal_places=2)
    width_cm = models.DecimalField("Ширина, см", max_digits=7, decimal_places=2)
    height_cm = models.DecimalField("Высота, см", max_digits=7, decimal_places=2)
    order_photo = models.FileField(
        "Фотография заказа",
        upload_to="orders/photos/",
        blank=True,
        help_text="Фото со всех сторон. Для документов, писем и конвертов - фото конверта или файла.",
    )
    declared_value = models.DecimalField("Ценность отправления", max_digits=10, decimal_places=2, default=0)
    urgency = models.BooleanField("Срочная доставка", default=False)
    delivery_price = models.DecimalField("Стоимость доставки", max_digits=10, decimal_places=2, default=0)
    status = models.CharField("Статус", max_length=30, choices=STATUS_CHOICES, default=STATUS_WAITING)
    delivery_attempts = models.PositiveSmallIntegerField("Попытки вручения", default=0)
    max_delivery_attempts = models.PositiveSmallIntegerField("Максимум попыток", default=3)
    confirmation_type = models.CharField(
        "Способ подтверждения",
        max_length=20,
        choices=CONFIRMATION_CHOICES,
        blank=True,
    )
    confirmation_value = models.CharField("Документальное подтверждение", max_length=255, blank=True)
    delivery_report_photo = models.FileField("Фотоотчет доставки", upload_to="orders/reports/", blank=True)
    client_confirmed_at = models.DateTimeField("Подтвержден клиентом", null=True, blank=True)
    delivered_at = models.DateTimeField("Дата вручения", null=True, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tracking_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["courier", "status"]),
        ]

    def __str__(self):
        return f"{self.tracking_number} - {self.get_status_display()}"

    @property
    def volume_m3(self):
        return (self.length_cm * self.width_cm * self.height_cm) / Decimal("1000000")

    @property
    def pickup_address_display(self):
        return f"{self.get_pickup_city_display()}, {self.pickup_street}, д. {self.pickup_house}"

    @property
    def delivery_address_display(self):
        if self.delivery_to_pickup_point:
            return f"{self.get_delivery_city_display()}, пункт выдачи"
        return f"{self.get_delivery_city_display()}, {self.delivery_street}, д. {self.delivery_house}"

    def clean(self):
        errors = {}
        for field in ("pickup_city", "pickup_street", "pickup_house", "delivery_city"):
            if not getattr(self, field):
                errors[field] = "Обязательное поле"
        if not self.delivery_to_pickup_point:
            if not self.delivery_street:
                errors["delivery_street"] = "Укажите улицу доставки"
            if not self.delivery_house:
                errors["delivery_house"] = "Укажите дом доставки"
        if not self.order_photo:
            errors["order_photo"] = "Добавьте фотографию заказа"
        for field in ("weight_kg", "length_cm", "width_cm", "height_cm"):
            value = getattr(self, field)
            if value is not None and value <= 0:
                errors[field] = "Значение должно быть больше нуля"
        if self.status == self.STATUS_DELIVERED_ADDRESS and not self.delivery_report_photo:
            errors["delivery_report_photo"] = "Для доставки по адресу нужен фотоотчет"
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
        self.pickup_address = self.pickup_address_display
        self.delivery_address = self.delivery_address_display
        self.distance_km = self.calculate_distance_km()
        self.delivery_price = self.calculate_delivery_price()
        if self.status in {self.STATUS_DELIVERED_PICKUP_POINT, self.STATUS_DELIVERED_ADDRESS} and not self.delivered_at:
            self.delivered_at = timezone.now()
        if self.status == self.STATUS_CONFIRMED and not self.client_confirmed_at:
            self.client_confirmed_at = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def generate_tracking_number(cls):
        while True:
            number = f"UP{timezone.now():%y%m%d}{uuid4().hex[:8].upper()}"
            if not cls.objects.filter(tracking_number=number).exists():
                return number

    def calculate_delivery_price(self):
        if not self.delivery_type_id:
            return Decimal("0.00")
        total = self.delivery_type.base_price
        if not self.delivery_to_pickup_point:
            total += self.ADDRESS_DELIVERY_SURCHARGE
        if self.weight_kg > self.INCLUDED_WEIGHT_KG:
            total += (self.weight_kg - self.INCLUDED_WEIGHT_KG) * self.OVERWEIGHT_PRICE_PER_KG
        for side in (self.length_cm, self.width_cm, self.height_cm):
            if side > self.INCLUDED_SIDE_CM:
                extra_blocks = ((side - self.INCLUDED_SIDE_CM) / Decimal("10")).to_integral_value(rounding=ROUND_CEILING)
                total += extra_blocks * self.OVERSIZE_PRICE_PER_10_CM
        if self.pickup_city != self.delivery_city:
            distance_blocks = (Decimal(self.calculate_distance_km()) / Decimal("10")).to_integral_value(rounding=ROUND_CEILING)
            total += distance_blocks * self.INTERCITY_PRICE_PER_10_KM
        return total.quantize(Decimal("0.01"))

    def calculate_distance_km(self):
        if self.pickup_city == self.delivery_city:
            return 0
        return self.CITY_DISTANCES_KM.get(frozenset((self.pickup_city, self.delivery_city)), 100)

    def set_status(self, new_status, user=None, comment="", location="", confirmation_type="", confirmation_value=""):
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValidationError("Неизвестный статус")
        if new_status != self.status and new_status not in self.STATUS_FLOW.get(self.status, set()):
            raise ValidationError(f"Нельзя изменить статус с '{self.get_status_display()}' на '{dict(self.STATUS_CHOICES)[new_status]}'")
        with transaction.atomic():
            self.status = new_status
            if confirmation_type:
                self.confirmation_type = confirmation_type
                self.confirmation_value = confirmation_value
            self.save()
            StatusHistory.objects.create(
                order=self,
                status=new_status,
                courier=user if getattr(user, "is_authenticated", False) else None,
                comment=comment,
                location=location,
            )
            AuditLog.objects.create(
                user=user if getattr(user, "is_authenticated", False) else None,
                order=self,
                action="status_changed",
                details=f"Статус изменен на {self.get_status_display()}. {comment}",
            )


class StatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history", verbose_name="Заказ")
    status = models.CharField("Статус", max_length=30, choices=Order.STATUS_CHOICES)
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Сотрудник",
    )
    comment = models.TextField("Комментарий", blank=True)
    location = models.CharField("Локация", max_length=200, blank=True)
    timestamp = models.DateTimeField("Время", auto_now_add=True)

    class Meta:
        verbose_name = "История статуса"
        verbose_name_plural = "История статусов"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.order.tracking_number}: {self.get_status_display()}"


class Issue(models.Model):
    ISSUE_TYPES = [
        ("no_answer", "Недозвон"),
        ("recipient_absent", "Получатель отсутствует"),
        ("refusal", "Отказ получателя"),
        ("damage", "Повреждение"),
        ("wrong_address", "Неверный адрес"),
        ("other", "Другое"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="issues", verbose_name="Заказ")
    issue_type = models.CharField("Тип ситуации", max_length=30, choices=ISSUE_TYPES)
    description = models.TextField("Описание")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Создал")
    resolved = models.BooleanField("Решена", default=False)
    resolved_at = models.DateTimeField("Дата решения", null=True, blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Исключительная ситуация"
        verbose_name_plural = "Исключительные ситуации"

    def save(self, *args, **kwargs):
        if self.resolved and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_issue_type_display()} для {self.order.tracking_number}"


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пользователь")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="audit_logs", verbose_name="Заказ")
    action = models.CharField("Действие", max_length=50)
    details = models.TextField("Детали", blank=True)
    created_at = models.DateTimeField("Время", auto_now_add=True)

    class Meta:
        verbose_name = "Журнал действий"
        verbose_name_plural = "Журнал действий"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%d.%m.%Y %H:%M} {self.action}"
