# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='date_created',
            field=models.DateField(default=datetime.datetime(2016, 4, 26, 15, 54, 22, 38710, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
