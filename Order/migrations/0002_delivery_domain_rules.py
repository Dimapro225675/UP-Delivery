# Generated manually for courier delivery domain rules.

from decimal import Decimal
from uuid import uuid4

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def fill_tracking_numbers(apps, schema_editor):
    Order = apps.get_model("Order", "Order")
    for order in Order.objects.filter(tracking_number__isnull=True):
        order.tracking_number = f"UP{timezone.now():%y%m%d}{uuid4().hex[:8].upper()}"
        order.save(update_fields=["tracking_number"])


def normalize_statuses(apps, schema_editor):
    mapping = {
        "new": "created",
        "assigned": "accepted",
        "picked_up": "in_transit",
        "in_progress": "in_transit",
        "in_transit": "in_transit",
        "delivered": "delivered",
        "cancelled": "cancelled",
    }
    Order = apps.get_model("Order", "Order")
    StatusHistory = apps.get_model("Order", "StatusHistory")
    for old, new in mapping.items():
        Order.objects.filter(status=old).update(status=new)
        StatusHistory.objects.filter(status=old).update(status=new)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("Order", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliverytype",
            name="declared_value_percent",
            field=models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=5, verbose_name="Процент от ценности"),
        ),
        migrations.AddField(
            model_name="deliverytype",
            name="price_per_kg",
            field=models.DecimalField(decimal_places=2, default=Decimal("30.00"), max_digits=10, verbose_name="Цена за кг"),
        ),
        migrations.AddField(
            model_name="deliverytype",
            name="price_per_m3",
            field=models.DecimalField(decimal_places=2, default=Decimal("500.00"), max_digits=10, verbose_name="Цена за м3"),
        ),
        migrations.AddField(
            model_name="deliverytype",
            name="urgency_multiplier",
            field=models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=5, verbose_name="Коэффициент срочности"),
        ),
        migrations.AddField(
            model_name="order",
            name="tracking_number",
            field=models.CharField(blank=True, editable=False, max_length=24, null=True, unique=True, verbose_name="Трекинг-номер"),
        ),
        migrations.AddField(
            model_name="order",
            name="cargo_type",
            field=models.CharField(
                choices=[
                    ("documents", "Документы"),
                    ("parcel", "Посылка"),
                    ("fragile", "Хрупкий груз"),
                    ("food", "Продукты"),
                    ("other", "Другое"),
                ],
                default="parcel",
                max_length=30,
                verbose_name="Тип отправления",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="cod_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Сумма наложенного платежа"),
        ),
        migrations.AddField(
            model_name="order",
            name="cod_collected_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Получено курьером"),
        ),
        migrations.AddField(
            model_name="order",
            name="cod_transferred_to_cashdesk",
            field=models.BooleanField(default=False, verbose_name="Передано в кассу"),
        ),
        migrations.AddField(
            model_name="order",
            name="confirmation_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("signature", "Электронная подпись"),
                    ("photo", "Фотоотчет"),
                    ("code", "Код подтверждения"),
                ],
                max_length=20,
                verbose_name="Способ подтверждения",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="confirmation_value",
            field=models.CharField(blank=True, max_length=255, verbose_name="Документальное подтверждение"),
        ),
        migrations.AddField(
            model_name="order",
            name="declared_value",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Ценность отправления"),
        ),
        migrations.AddField(
            model_name="order",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Дата вручения"),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_attempts",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Попытки вручения"),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Стоимость доставки"),
        ),
        migrations.AddField(
            model_name="order",
            name="distance_km",
            field=models.PositiveIntegerField(default=1, verbose_name="Расстояние, км"),
        ),
        migrations.AddField(
            model_name="order",
            name="height_cm",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=7, verbose_name="Высота, см"),
        ),
        migrations.AddField(
            model_name="order",
            name="length_cm",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=7, verbose_name="Длина, см"),
        ),
        migrations.AddField(
            model_name="order",
            name="max_delivery_attempts",
            field=models.PositiveSmallIntegerField(default=3, verbose_name="Максимум попыток"),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_type",
            field=models.CharField(
                choices=[("prepaid", "Предоплата"), ("cod", "Наложенный платеж")],
                default="prepaid",
                max_length=20,
                verbose_name="Тип оплаты",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="sender_payout_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="К переводу отправителю"),
        ),
        migrations.AddField(
            model_name="order",
            name="urgency",
            field=models.BooleanField(default=False, verbose_name="Срочная доставка"),
        ),
        migrations.AddField(
            model_name="order",
            name="weight_kg",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=7, verbose_name="Вес, кг"),
        ),
        migrations.AddField(
            model_name="order",
            name="width_cm",
            field=models.DecimalField(decimal_places=2, default=1, max_digits=7, verbose_name="Ширина, см"),
        ),
        migrations.RunPython(fill_tracking_numbers, migrations.RunPython.noop),
        migrations.RunPython(normalize_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="tracking_number",
            field=models.CharField(editable=False, max_length=24, unique=True, verbose_name="Трекинг-номер"),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("created", "Создано"),
                    ("accepted", "Принято на складе"),
                    ("in_transit", "В пути"),
                    ("delivered", "Доставлено"),
                    ("returned", "Возврат"),
                    ("cancelled", "Отменено"),
                ],
                default="created",
                max_length=20,
                verbose_name="Статус",
            ),
        ),
        migrations.AlterField(
            model_name="statushistory",
            name="status",
            field=models.CharField(
                choices=[
                    ("created", "Создано"),
                    ("accepted", "Принято на складе"),
                    ("in_transit", "В пути"),
                    ("delivered", "Доставлено"),
                    ("returned", "Возврат"),
                    ("cancelled", "Отменено"),
                ],
                max_length=20,
                verbose_name="Статус",
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="issue_type",
            field=models.CharField(
                choices=[
                    ("no_answer", "Недозвон"),
                    ("recipient_absent", "Получатель отсутствует"),
                    ("refusal", "Отказ получателя"),
                    ("damage", "Повреждение"),
                    ("wrong_address", "Неверный адрес"),
                    ("payment_issue", "Проблема с оплатой"),
                    ("other", "Другое"),
                ],
                max_length=30,
                verbose_name="Тип ситуации",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="created_at",
            field=models.DateTimeField(default=timezone.now, verbose_name="Создана"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="issue",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Создана"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                choices=[("card", "Карта онлайн"), ("cash", "Наличные"), ("cod", "Наложенный платеж")],
                max_length=20,
                verbose_name="Способ оплаты",
            ),
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=50, verbose_name="Действие")),
                ("details", models.TextField(blank=True, verbose_name="Детали")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Время")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_logs", to="Order.order", verbose_name="Заказ")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name="Пользователь")),
            ],
            options={
                "verbose_name": "Журнал действий",
                "verbose_name_plural": "Журнал действий",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["tracking_number"], name="Order_order_trackin_3b3bf1_idx")),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["status"], name="Order_order_status_4303ad_idx")),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["courier", "status"], name="Order_order_courie_75989f_idx")),
    ]
