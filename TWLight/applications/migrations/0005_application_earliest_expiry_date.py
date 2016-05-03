# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0004_auto_20160427_2120'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='earliest_expiry_date',
            field=models.DateField(help_text='Do not override this field! Its value is set automatically when the application is saved, and overriding it may have undesirable results.', null=True, blank=True),
            preserve_default=True,
        ),
    ]
