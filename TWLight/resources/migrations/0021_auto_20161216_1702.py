# -*- coding: utf-8 -*-
"""
We need to move from our earlier DurationField to the now-built-in Django
DurationField. In migration 19 we created the new field; in 20 we copied over
the data. In this migration we delete the old field. In 22 we'll rename it so
that it presents the prior API.
"""
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0020_move_to_internal_durationfield'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='partner',
            name='access_grant_term',
        ),
        migrations.AlterField(
            model_name='partner',
            name='access_grant_term_pythonic',
            field=models.DurationField(default=datetime.timedelta(365), help_text='The standard length of an access grant from this Partner. Entered as <days hours:minutes:seconds>. Defaults to 365 days.', null=True, blank=True),
        ),
    ]
