# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0003_application_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='partner',
            field=models.ForeignKey(related_name='applications', to='resources.Partner'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.IntegerField(default=0, choices=[(0, 'Pending'), (1, 'Under discussion'), (2, 'Approved'), (3, 'Not approved')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='application',
            name='user',
            field=models.ForeignKey(related_name='applications', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
