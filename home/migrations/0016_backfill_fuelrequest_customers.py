from django.conf import settings
from django.db import migrations


def attach_existing_requests_to_phone_accounts(apps, schema_editor):
    FuelRequest = apps.get_model("home", "FuelRequest")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    database = schema_editor.connection.alias

    for request in FuelRequest.objects.using(database).filter(customer__isnull=True).only("id", "phone").iterator():
        user_id = User.objects.using(database).filter(username=request.phone).values_list("pk", flat=True).first()
        if user_id:
            FuelRequest.objects.using(database).filter(pk=request.pk).update(customer_id=user_id)


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0015_fuelrequest_customer"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(attach_existing_requests_to_phone_accounts, migrations.RunPython.noop),
    ]
