# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0014_auto_20160908_1410")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="use_wp_email",
            field=models.BooleanField(
                default=True,
                help_text="Should we automatically update their email from their Wikipedia email when they log in? Defaults to True.",
            ),
        )
    ]
