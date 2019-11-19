# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("applications", "0010_auto_20160706_1409")]

    operations = [
        migrations.AlterModelOptions(
            name="application",
            options={
                "ordering": ["-date_created", "editor", "partner"],
                "verbose_name": "application",
                "verbose_name_plural": "applications",
            },
        )
    ]
