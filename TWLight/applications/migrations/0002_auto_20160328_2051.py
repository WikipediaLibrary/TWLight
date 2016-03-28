# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='application',
            old_name='agreement_with_terms',
            new_name='agreement_with_terms_of_use',
        ),
        migrations.RenameField(
            model_name='application',
            old_name='stream_requested',
            new_name='specific_stream',
        ),
        migrations.RenameField(
            model_name='application',
            old_name='title_requested',
            new_name='specific_title',
        ),
    ]
