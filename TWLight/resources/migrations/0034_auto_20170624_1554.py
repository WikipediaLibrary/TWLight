# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0033_auto_20170621_0822'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='description_en',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='stream',
            name='description_fi',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='stream',
            name='description_fr',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
    ]
