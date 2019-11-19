# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [("resources", "0004_auto_20160509_1817")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="date_created",
            field=models.DateField(
                default=datetime.datetime(2016, 5, 9, 19, 18, 3, 475335, tzinfo=utc),
                auto_now_add=True,
            ),
            preserve_default=False,
        )
    ]
