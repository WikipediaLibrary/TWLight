# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0016_auto_20170707_1552'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='imported',
            field=models.BooleanField(blank=True, null=True, default=False),
        ),
    ]
