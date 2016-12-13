# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0017_auto_20161208_1940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(help_text="Organizational role or job title. This is NOT intended to be used for honorifics. Think 'Director of Editorial Services', not 'Ms.'", max_length=75),
            preserve_default=True,
        ),
    ]
