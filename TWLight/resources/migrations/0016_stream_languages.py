# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("resources", "0015_auto_20161208_1526")]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="languages",
            field=models.ManyToManyField(
                to="resources.Language", null=True, blank=True
            ),
            preserve_default=True,
        )
    ]
