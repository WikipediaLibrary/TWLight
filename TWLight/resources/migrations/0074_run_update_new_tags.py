from django.core.management import call_command
from django.db import migrations


def update_new_tags(apps, schema_editor):
    call_command("update_new_tags")


class Migration(migrations.Migration):

    dependencies = [("resources", "0073_stream_description_it")]

    operations = [migrations.RunPython(update_new_tags, migrations.RunPython.noop)]
