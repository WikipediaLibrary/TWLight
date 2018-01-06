# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0036_auto_20170716_1235'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='bundle',
            field=models.NullBooleanField(default=False, help_text='Is this partner a part of the Bundle?'),
        ),
    ]
