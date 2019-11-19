# -*- coding: utf-8 -*-


from django.db import models, migrations

from ..groups import RESTRICTED_GROUP_NAME


def create_restricted(apps, schema_editor):
    """
    Ensure that the Restricted group is created.
    """
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=RESTRICTED_GROUP_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0025_userprofile_data_restricted"),
        ("auth", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_restricted)]
