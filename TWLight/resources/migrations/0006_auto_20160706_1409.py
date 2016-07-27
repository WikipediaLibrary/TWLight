# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0005_partner_date_created'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='contact',
            options={'verbose_name': 'contact person', 'verbose_name_plural': 'contact people'},
        ),
        migrations.AlterModelOptions(
            name='partner',
            options={'verbose_name': 'partner', 'verbose_name_plural': 'partners'},
        ),
        migrations.AlterModelOptions(
            name='stream',
            options={'verbose_name': 'collection', 'verbose_name_plural': 'collections'},
        ),
    ]
