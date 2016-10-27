# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0010_auto_20161024_1942'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partner',
            name='company_name',
            field=models.CharField(help_text="Partner organization's name (e.g. McFarland). Note: this will be user-visible and *not translated*.", max_length=40),
            preserve_default=True,
        ),
    ]
