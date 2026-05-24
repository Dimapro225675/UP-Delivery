# Generated manually for delivery roles.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("client", "Клиент"),
                    ("courier", "Курьер"),
                    ("dispatcher", "Диспетчер"),
                    ("admin", "Администратор"),
                ],
                default="client",
                max_length=20,
                verbose_name="Роль",
            ),
        ),
    ]
