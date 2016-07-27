# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0005_application_earliest_expiry_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='days_open',
            field=models.IntegerField(help_text='Do not override this field! Its value is set automatically when the application is saved, and overriding it may have undesirable results.', null=True, blank=True),
            preserve_default=True,
        ),
    ]
