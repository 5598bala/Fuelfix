from django.db import migrations


def create_missing_table(apps, schema_editor):
    connection = schema_editor.connection
    table_name = "socialaccount_socialapp_sites"

    if table_name in connection.introspection.table_names():
        return

    SocialApp = apps.get_model("socialaccount", "SocialApp")
    Site = apps.get_model("sites", "Site")

    SocialAppSites = SocialApp._meta.get_field("sites").remote_field.through

    schema_editor.create_model(SocialAppSites)


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0001_initial"),  # Replace with your actual latest home migration
        ("socialaccount", "0006_alter_socialaccount_extra_data"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_table,
            migrations.RunPython.noop,
        ),
    ]