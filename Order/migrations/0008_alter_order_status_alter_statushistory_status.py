from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Order", "0007_multiple_photos_and_cleanup_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("waiting", "В ожидании"),
                    ("waiting_courier", "В ожидании курьера"),
                    ("delivering", "Доставляется"),
                    ("delivered_pickup_point", "Доставлен на пункт выдачи"),
                    ("delivered_address", "Доставлен на адрес доставки"),
                    ("confirmed", "Подтвержден клиентом"),
                    ("returned", "Возврат"),
                    ("cancelled", "Отменено"),
                ],
                default="waiting",
                max_length=30,
                verbose_name="Статус",
            ),
        ),
        migrations.AlterField(
            model_name="statushistory",
            name="status",
            field=models.CharField(
                choices=[
                    ("waiting", "В ожидании"),
                    ("waiting_courier", "В ожидании курьера"),
                    ("delivering", "Доставляется"),
                    ("delivered_pickup_point", "Доставлен на пункт выдачи"),
                    ("delivered_address", "Доставлен на адрес доставки"),
                    ("confirmed", "Подтвержден клиентом"),
                    ("returned", "Возврат"),
                    ("cancelled", "Отменено"),
                ],
                max_length=30,
                verbose_name="Статус",
            ),
        ),
    ]
