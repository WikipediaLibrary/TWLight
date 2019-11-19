# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [("applications", "0016_auto_20170707_1552")]

    operations = [
        migrations.AddField(
            model_name="application",
            name="imported",
            field=models.NullBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="application",
            name="date_created",
            field=models.DateField(default=django.utils.timezone.now, editable=False),
        ),
    ]
