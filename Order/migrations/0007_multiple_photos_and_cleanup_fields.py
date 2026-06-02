from django.db import migrations, models


def migrate_single_photos_to_galleries(apps, schema_editor):
    Order = apps.get_model("Order", "Order")
    OrderPhoto = apps.get_model("Order", "OrderPhoto")
    DeliveryReportPhoto = apps.get_model("Order", "DeliveryReportPhoto")

    for order in Order.objects.exclude(order_photo="").iterator():
        if order.order_photo:
            OrderPhoto.objects.create(order_id=order.pk, image=order.order_photo)

    for order in Order.objects.exclude(delivery_report_photo="").iterator():
        if order.delivery_report_photo:
            DeliveryReportPhoto.objects.create(order_id=order.pk, image=order.delivery_report_photo)


class Migration(migrations.Migration):
    dependencies = [
        ("Order", "0006_remove_order_cod_amount_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.FileField(upload_to="orders/photos/", verbose_name="Фотография заказа")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")),
                ("order", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="order_photos", to="Order.order", verbose_name="Заказ")),
            ],
            options={
                "verbose_name": "Фотография заказа",
                "verbose_name_plural": "Фотографии заказа",
                "ordering": ["created_at", "pk"],
            },
        ),
        migrations.CreateModel(
            name="DeliveryReportPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.FileField(upload_to="orders/reports/", verbose_name="Фотоотчет доставки")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")),
                ("order", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="delivery_report_photos", to="Order.order", verbose_name="Заказ")),
            ],
            options={
                "verbose_name": "Фотоотчет доставки",
                "verbose_name_plural": "Фотоотчеты доставки",
                "ordering": ["created_at", "pk"],
            },
        ),
        migrations.RunPython(migrate_single_photos_to_galleries, migrations.RunPython.noop),
        migrations.RemoveField(model_name="deliverytype", name="declared_value_percent"),
        migrations.RemoveField(model_name="deliverytype", name="price_per_kg"),
        migrations.RemoveField(model_name="deliverytype", name="price_per_m3"),
        migrations.RemoveField(model_name="deliverytype", name="urgency_multiplier"),
        migrations.RemoveField(model_name="order", name="delivery_attempts"),
        migrations.RemoveField(model_name="order", name="delivery_report_photo"),
        migrations.RemoveField(model_name="order", name="max_delivery_attempts"),
        migrations.RemoveField(model_name="order", name="order_photo"),
    ]
