# -*- coding: utf-8 -*-
"""
We need to move from our earlier DurationField to the now-built-in Django
DurationField. In migration 19 we created the new field; in this migration we
copy over the data. In 21 we'll delete the old field, and in 22 we'll rename the
new one to the old name so as to present the expected API.
"""
from __future__ import unicode_literals

from django.db import migrations, models


def copy_access_grant_terms(apps, schema_editor):
    Partner = apps.get_model('resources', 'Partner')
    # Although this looks like it should only get AVAILABLE Partners (since
    # we've defined a custom manager), in fact it uses the Django default
    # internal manager and finds all Partners.
    for partner in Partner.objects.all():
        partner.access_grant_term_pythonic = partner.access_grant_term
        partner.save()


def delete_access_grant_terms(apps, schema_editor):
    Partner = apps.get_model('resources', 'Partner')
    for partner in Partner.objects.all():
        partner.access_grant_term_pythonic = None
        partner.save()



class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0019_auto_20161216_1650'),
    ]

    operations = [
        migrations.RunPython(copy_access_grant_terms,
            reverse_code=delete_access_grant_terms),
    ]
