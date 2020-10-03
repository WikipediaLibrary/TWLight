# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("resources", "0011_auto_20161027_1836")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="status",
            field=models.IntegerField(
                default=1, choices=[(0, "Available"), (1, "Not available")]
            ),
            preserve_default=True,
        )
    ]
