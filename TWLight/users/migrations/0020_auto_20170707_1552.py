# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [("users", "0019_auto_20170621_0822")]

    operations = [
        migrations.AlterField(
            model_name="editor",
            name="date_created",
            field=models.DateField(
                default=django.utils.timezone.now,
                help_text="When this profile was first created",
                editable=False,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="editor",
            name="last_updated",
            field=models.DateField(
                default=django.utils.timezone.now,
                help_text="When this information was last edited",
                blank=True,
            ),
        ),
    ]
