# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0004_auto_20160401_2008'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='specific_stream',
            field=models.ForeignKey(related_name='applications', blank=True, to='resources.Stream', null=True),
            preserve_default=True,
        ),
    ]
