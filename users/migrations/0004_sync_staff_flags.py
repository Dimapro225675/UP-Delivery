from django.db import migrations


def sync_staff_flags(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.filter(is_superuser=True).update(is_staff=True)
    CustomUser.objects.filter(role__in=["dispatcher", "admin"]).update(is_staff=True)
    CustomUser.objects.exclude(role__in=["dispatcher", "admin"]).filter(is_superuser=False).update(is_staff=False)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_alter_customuser_email_alter_customuser_full_name_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_staff_flags, migrations.RunPython.noop),
    ]
