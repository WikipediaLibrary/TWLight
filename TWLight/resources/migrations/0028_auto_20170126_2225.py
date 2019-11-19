# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0027_auto_20170117_2046")]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="status",
            field=models.IntegerField(
                default=1,
                help_text="Should this Partner be displayed to end users? Is it open for applications right now?",
                choices=[(0, "Available"), (1, "Not available"), (2, "Waitlisted")],
            ),
        )
    ]
