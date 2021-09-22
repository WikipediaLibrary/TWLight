from django.core.management import call_command
from django.db import migrations


def update_new_tags(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [("resources", "0074_auto_20210601_1629")]

    operations = [migrations.RunPython(update_new_tags, migrations.RunPython.noop)]
