
import uuid

from django.db import migrations, models


def fix_duplicate_tracking_tokens(apps, schema_editor):
    FuelRequest = apps.get_model("home", "FuelRequest")
    database = schema_editor.connection.alias

    used_tokens = set()

    requests = (
        FuelRequest.objects.using(database)
        .order_by("pk")
        .iterator()
    )

    for request in requests:
        token = request.tracking_token

        if token is None or token in used_tokens:
            token = uuid.uuid4()

            while token in used_tokens:
                token = uuid.uuid4()

            request.tracking_token = token
            request.save(
                using=database,
                update_fields=["tracking_token"],
            )

        used_tokens.add(token)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0010_populate_tracking_tokens"),
    ]

    operations = [
        migrations.RunPython(
            fix_duplicate_tracking_tokens,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="fuelrequest",
            name="tracking_token",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
            ),
        ),
    ]
