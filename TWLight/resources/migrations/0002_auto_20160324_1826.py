# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("resources", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="stream",
            name="name",
            field=models.CharField(
                help_text=b"Name of stream (e.g. 'Health and Behavioral Sciences). Will be user-visible and *not translated*. Do not include the name of the partner here. If partner name and resource name need to be presented together, templates are responsible for presenting them in a format that can be internationalized.",
                max_length=50,
            ),
            preserve_default=True,
        )
    ]
