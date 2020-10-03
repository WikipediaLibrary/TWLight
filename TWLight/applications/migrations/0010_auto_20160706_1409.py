# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("applications", "0009_auto_20160527_1505")]

    operations = [
        migrations.AlterModelOptions(
            name="application",
            options={
                "verbose_name": "application",
                "verbose_name_plural": "applications",
            },
        )
    ]
