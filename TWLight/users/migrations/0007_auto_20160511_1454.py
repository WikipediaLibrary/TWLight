# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("users", "0006_auto_20160428_1703")]

    operations = [
        migrations.RenameField(
            model_name="editor", old_name="account_created", new_name="date_created"
        )
    ]
