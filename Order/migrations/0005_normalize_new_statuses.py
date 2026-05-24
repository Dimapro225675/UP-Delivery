from django.db import migrations


def normalize_statuses(apps, schema_editor):
    mapping = {
        "created": "waiting",
        "accepted": "waiting_courier",
        "in_transit": "delivering",
        "delivered": "delivered_address",
    }
    Order = apps.get_model("Order", "Order")
    StatusHistory = apps.get_model("Order", "StatusHistory")
    for old, new in mapping.items():
        Order.objects.filter(status=old).update(status=new)
        StatusHistory.objects.filter(status=old).update(status=new)


class Migration(migrations.Migration):

    dependencies = [
        ("Order", "0004_order_client_confirmed_at_order_delivery_city_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_statuses, migrations.RunPython.noop),
    ]
