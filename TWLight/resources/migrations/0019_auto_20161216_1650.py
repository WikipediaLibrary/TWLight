# -*- coding: utf-8 -*-
"""
We need to move from our earlier DurationField to the now-built-in Django
DurationField. In this migration we create the new field; in migration 20 we'll
copy over the data. In 21 we'll delete the old field, and in 22 we'll rename the
new one to the old name so as to present the expected API.
"""

from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0018_auto_20161213_1603'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='access_grant_term_pythonic',
            field=models.DurationField(default=datetime.timedelta(365), null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
