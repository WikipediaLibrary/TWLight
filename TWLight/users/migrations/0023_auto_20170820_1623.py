# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0022_auto_20170815_1123")]

    operations = [
        migrations.AlterField(
            model_name="editor",
            name="wp_editcount",
            field=models.IntegerField(
                help_text="Wikipedia edit count", null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="editor",
            name="wp_registered",
            field=models.DateField(
                help_text="Date registered at Wikipedia", null=True, blank=True
            ),
        ),
    ]
