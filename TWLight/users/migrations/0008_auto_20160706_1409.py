# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("users", "0007_auto_20160511_1454")]

    operations = [
        migrations.AlterModelOptions(
            name="editor",
            options={
                "verbose_name": "wikipedia editor",
                "verbose_name_plural": "wikipedia editors",
            },
        ),
        migrations.AlterField(
            model_name="editor",
            name="date_created",
            field=models.DateField(
                help_text="When this profile was first created", auto_now_add=True
            ),
            preserve_default=True,
        ),
    ]
