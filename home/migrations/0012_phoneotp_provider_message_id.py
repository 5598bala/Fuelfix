from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0011_alter_fuelrequest_tracking_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="phoneotp",
            name="provider_message_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=128),
        ),
        migrations.RemoveField(
            model_name="phoneotp",
            name="otp_hash",
        ),
    ]
