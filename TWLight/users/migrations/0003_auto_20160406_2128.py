# -*- coding: utf-8 -*-


from django.db import models, migrations

from ..groups import COORDINATOR_GROUP_NAME


def create_coordinators(apps, schema_editor):
    """
    Ensure that the Coordinators group is created.
    """
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=COORDINATOR_GROUP_NAME)


class Migration(migrations.Migration):

    dependencies = [("users", "0002_auto_20160328_2031"), ("auth", "0001_initial")]

    operations = [migrations.RunPython(create_coordinators)]
