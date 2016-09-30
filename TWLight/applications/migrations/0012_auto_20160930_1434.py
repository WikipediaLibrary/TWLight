# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0011_auto_20160908_1410'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, 'Pending'), (1, 'Under discussion'), (2, 'Approved'), (3, 'Not approved'), (4, 'Sent to partner')]),
            preserve_default=True,
        ),
    ]
