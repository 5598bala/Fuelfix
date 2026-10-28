import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_default_sos_options(apps, schema_editor):
    SOSOption = apps.get_model("home", "SOSOption")
    defaults = [
        ("fuel", "Request urgent fuel", "Send an urgent fuel delivery request", "", 1),
        ("mechanic", "Request a mechanic", "Tell us what happened and where you are", "", 2),
        ("support", "Call FuelFix support", "Tap to call FuelFix support", "6382592643", 3),
        ("share_location", "Share my live location", "Share a live link with FuelFix support", "", 4),
    ]
    for action, label, description, phone, order in defaults:
        SOSOption.objects.get_or_create(
            action=action,
            defaults={"label": label, "description": description, "phone": phone, "display_order": order, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0012_phoneotp_provider_message_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MechanicRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=15)),
                ("address", models.TextField()),
                ("issue_description", models.TextField()),
                ("latitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ("status", models.CharField(choices=[("new", "New request"), ("contacted", "Customer contacted"), ("in_progress", "In progress"), ("resolved", "Resolved")], default="new", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mechanic_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SOSLocationShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("session_key", models.CharField(db_index=True, max_length=40, unique=True)),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("accuracy_meters", models.FloatField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sos_location_shares", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"], "verbose_name": "SOS live location share", "verbose_name_plural": "SOS live location shares"},
        ),
        migrations.CreateModel(
            name="SOSOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("fuel", "Request urgent fuel"), ("mechanic", "Request a mechanic"), ("support", "Call FuelFix support"), ("share_location", "Share my live location")], max_length=24, unique=True)),
                ("label", models.CharField(max_length=80)),
                ("description", models.CharField(blank=True, max_length=180)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["display_order", "id"], "verbose_name": "SOS menu option", "verbose_name_plural": "SOS menu options"},
        ),
        migrations.RunPython(create_default_sos_options, migrations.RunPython.noop),
    ]
