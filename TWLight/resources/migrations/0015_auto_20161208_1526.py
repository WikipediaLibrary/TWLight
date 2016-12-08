# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def initialize_languages(apps, schema_editor):
    """
    Make sure the database starts with a few languages we know Partners offer.
    (This will also make it easier for administrators to use the language
    field in the admin site.)
    """
    Language = apps.get_model("resources", "Language")
    basic_codes = ['en', 'fr', 'fa']
    for code in basic_codes:
        lang = Language(language=code)
        lang.save()

class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0014_auto_20161208_1520'),
    ]

    operations = [
        migrations.RunPython(initialize_languages)
    ]
