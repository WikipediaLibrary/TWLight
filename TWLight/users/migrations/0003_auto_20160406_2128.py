# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from ..models import COORDINATOR_GROUP_NAME


def create_coordinators(apps, schema_editor):
    """
    Ensure that the Coordinators group is created.
    """
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name=COORDINATOR_GROUP_NAME)   


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20160328_2031'),
    ]

    operations = [
        migrations.RunPython(create_coordinators)
    ]
