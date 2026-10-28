
import uuid

from django.db import migrations


def populate_tracking_tokens(apps, schema_editor):
    FuelRequest = apps.get_model("home", "FuelRequest")
    database = schema_editor.connection.alias

    for request in (
        FuelRequest.objects.using(database)
        .filter(tracking_token__isnull=True)
        .iterator()
    ):
        request.tracking_token = uuid.uuid4()
        request.save(update_fields=["tracking_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0009_fuelrequest_tracking_token_provider_is_online_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_tracking_tokens,
            migrations.RunPython.noop,
        ),
    ]