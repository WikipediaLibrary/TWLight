# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("applications", "0002_application_date_created")]

    operations = [
        migrations.AddField(
            model_name="application",
            name="date_closed",
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        )
    ]
