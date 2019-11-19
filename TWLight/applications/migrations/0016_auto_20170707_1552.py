# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [("applications", "0015_auto_20170621_0822")]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="date_created",
            field=models.DateField(
                default=django.utils.timezone.now, editable=False, blank=True
            ),
        )
    ]
