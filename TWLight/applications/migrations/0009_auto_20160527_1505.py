# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("applications", "0008_auto_20160527_1502")]

    operations = [
        migrations.RemoveField(model_name="application", name="user"),
        migrations.AlterField(
            model_name="application",
            name="editor",
            field=models.ForeignKey(
                related_name="applications", default=1, to="users.Editor"
            ),
            preserve_default=False,
        ),
    ]
