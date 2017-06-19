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
            field=models.DateField(help_text='Please do not override this field! It is set automatically.', null=True, blank=True),
            preserve_default=True,
        ),
    ]
