from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Order", "0008_alter_order_status_alter_statushistory_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderHistoryHiddenEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Скрыт")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="hidden_in_history_entries",
                        to="Order.order",
                        verbose_name="Заказ",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="hidden_order_history_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Скрытая запись истории",
                "verbose_name_plural": "Скрытые записи истории",
            },
        ),
        migrations.AddConstraint(
            model_name="orderhistoryhiddenentry",
            constraint=models.UniqueConstraint(fields=("user", "order"), name="unique_hidden_order_history_entry"),
        ),
    ]
