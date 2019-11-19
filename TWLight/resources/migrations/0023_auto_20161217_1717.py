# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0022_auto_20161216_1704")]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="description",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="stream",
            name="description",
            field=models.TextField(
                help_text="Optional description of this stream's contents. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.",
                null=True,
                blank=True,
            ),
        ),
    ]
