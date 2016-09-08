# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0007_auto_20160721_1750'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='partner',
            options={'ordering': ['company_name'], 'verbose_name': 'partner', 'verbose_name_plural': 'partners'},
        ),
        migrations.AlterModelOptions(
            name='stream',
            options={'ordering': ['partner', 'name'], 'verbose_name': 'collection', 'verbose_name_plural': 'collections'},
        ),
        migrations.AlterField(
            model_name='partner',
            name='terms_of_use',
            field=models.URLField(help_text='Link to terms of use. Required if this company requires that users agree to terms of use as a condition of applying for access; optional otherwise.', null=True, blank=True),
            preserve_default=True,
        ),
    ]
