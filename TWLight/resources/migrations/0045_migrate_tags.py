# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from django.conf import settings
from django.core import serializers

from TWLight.resources.models import TextFieldTag, Partner
from taggit.models import Tag, TaggedItem
from taggit.managers import TaggableManager

# Migrate the existing tag objects to the model that lives in resources.
def copy_tags(apps, schema_editor):
    for old_tag in Tag.objects.all():
       new_tag = TextFieldTag()
       new_tag.name = old_tag.name
       new_tag.slug = old_tag.slug
       new_tag.save()

# Apply data from old tag field to the new tag field
def retag_partners(apps, schema_editor):
    for partner in Partner.objects.all():
        old_tags = partner.old_tags.all()
        for old_tag in old_tags:
            partner.tags.add(old_tag.name)
            partner.save()

# Delete the old tag data
def delete_old_tags(apps, schema_editor):
    for old_tag in Tag.objects.all():
       old_tag.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        ('resources', '0044_auto_20180612_0201'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='old_tags',
            field=TaggableManager(blank=True, help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Old Tags'),
        ),
        migrations.RunPython(copy_tags),
        migrations.RunPython(retag_partners),
        migrations.RunPython(delete_old_tags),
        migrations.RemoveField(model_name='partner',name='old_tags'),
    ]
