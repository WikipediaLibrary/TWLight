# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("resources", "0002_auto_20160324_1826")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="access_grant_term",
            field=models.DurationField(
                help_text=b"The standard length of an access grant from this Partner.",
                null=True,
                blank=True,
            ),
            preserve_default=True,
        )
    ]
