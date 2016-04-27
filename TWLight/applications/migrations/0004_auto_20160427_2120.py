# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0003_application_date_closed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='date_closed',
            field=models.DateField(help_text='Do not override this field! Its value is set automatically when the application is saved, and overriding it may have undesirable results.', null=True, blank=True),
            preserve_default=True,
        ),
    ]
