# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0017_auto_20170709_1859'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='already_signed_up',
            field=models.BooleanField(default=False),
        ),
    ]
