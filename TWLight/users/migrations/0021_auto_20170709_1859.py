# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [("users", "0020_auto_20170707_1552")]

    operations = [
        migrations.AlterField(
            model_name="editor",
            name="date_created",
            field=models.DateField(
                default=django.utils.timezone.now,
                help_text="When this profile was first created",
                editable=False,
            ),
        ),
        migrations.AlterField(
            model_name="editor",
            name="last_updated",
            field=models.DateField(
                default=django.utils.timezone.now,
                help_text="When this information was last edited",
            ),
        ),
    ]
