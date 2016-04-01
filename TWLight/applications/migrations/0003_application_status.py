# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0002_auto_20160328_2051'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, b'Pending'), (1, b'Question'), (2, b'Approved'), (3, b'Not approved')]),
            preserve_default=True,
        ),
    ]
