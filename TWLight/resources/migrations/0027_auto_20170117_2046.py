# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0026_partner_coordinator")]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="languages",
            field=models.ManyToManyField(
                help_text="Select all languages in which this partner publishes content.",
                to="resources.Language",
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="stream",
            name="languages",
            field=models.ManyToManyField(to="resources.Language", blank=True),
        ),
    ]
