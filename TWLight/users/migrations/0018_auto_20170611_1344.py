# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0017_auto_20170221_1502")]

    operations = [
        migrations.AlterField(
            model_name="editor",
            name="wp_sub",
            field=models.IntegerField(help_text="Wikipedia user ID", unique=True),
        ),
        migrations.AlterUniqueTogether(name="editor", unique_together=set([])),
        migrations.RemoveField(model_name="editor", name="home_wiki"),
    ]
