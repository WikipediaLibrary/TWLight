# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0008_auto_20160908_1410'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(help_text='Organizational role or job title. This is NOT intended to be used for honorifics like Mr., Ms., Mx., etc.', max_length=30),
            preserve_default=True,
        ),
    ]
