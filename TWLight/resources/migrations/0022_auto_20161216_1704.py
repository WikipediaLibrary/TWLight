# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0021_auto_20161216_1702")]

    operations = [
        migrations.RenameField(
            model_name="partner",
            old_name="access_grant_term_pythonic",
            new_name="access_grant_term",
        )
    ]
