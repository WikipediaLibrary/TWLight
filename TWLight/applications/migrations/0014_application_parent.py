# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("applications", "0013_application_sent_by")]

    operations = [
        migrations.AddField(
            model_name="application",
            name="parent",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                blank=True,
                to="applications.Application",
                null=True,
            ),
        )
    ]
