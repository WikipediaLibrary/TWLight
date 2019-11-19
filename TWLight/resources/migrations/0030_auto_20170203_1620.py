# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [("resources", "0029_partner_tags")]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="tags",
            field=taggit.managers.TaggableManager(
                to="taggit.Tag",
                through="taggit.TaggedItem",
                blank=True,
                help_text="A comma-separated list of tags.",
                verbose_name="Tags",
            ),
        )
    ]
