# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_auto_20160721_2006'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='editor',
            unique_together=set([('wp_sub', 'home_wiki')]),
        ),
    ]
