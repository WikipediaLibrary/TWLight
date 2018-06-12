# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from django.conf import settings
from django.core import serializers

from TWLight.resources.models import TextFieldTag, Partner
from taggit.models import Tag, TaggedItem

def migrate_tags(apps, schema_editor):
    for oldtag in Tag.objects.all():
       newtag = TextFieldTag()
       newtag.name = oldtag.name
       newtag.slug = oldtag.slug
       newtag.save()

# Needs to be worked out
#def migrate_tagged_items(apps, schema_editor):
#    for tagged_item in TaggedItem.objects.all():

class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0044_auto_20180612_0201'),
    ]

    operations = [
        migrations.RunPython(migrate_tags),
# needs to be worked out
#        migrations.RunPython(migrate_tagged_items),
    ]
