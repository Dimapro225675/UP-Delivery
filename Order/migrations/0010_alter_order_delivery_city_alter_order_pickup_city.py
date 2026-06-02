from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("Order", "0009_orderhistoryhiddenentry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="delivery_city",
            field=models.CharField(
                choices=[
                    ("moscow", "Москва"),
                    ("tver", "Тверь"),
                    ("kaluga", "Калуга"),
                    ("spb", "Санкт-Петербург"),
                    ("kazan", "Казань"),
                    ("nizhny", "Нижний Новгород"),
                    ("ekb", "Екатеринбург"),
                ],
                default="moscow",
                max_length=40,
                verbose_name="Город доставки",
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="pickup_city",
            field=models.CharField(
                choices=[
                    ("moscow", "Москва"),
                    ("tver", "Тверь"),
                    ("kaluga", "Калуга"),
                    ("spb", "Санкт-Петербург"),
                    ("kazan", "Казань"),
                    ("nizhny", "Нижний Новгород"),
                    ("ekb", "Екатеринбург"),
                ],
                default="moscow",
                max_length=40,
                verbose_name="Город забора",
            ),
        ),
    ]
