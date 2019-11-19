# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0035_partner_send_instructions")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="send_instructions_en",
            field=models.TextField(
                help_text="Optional instructions for sending application data to this partner.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="send_instructions_fi",
            field=models.TextField(
                help_text="Optional instructions for sending application data to this partner.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="send_instructions_fr",
            field=models.TextField(
                help_text="Optional instructions for sending application data to this partner.",
                null=True,
                blank=True,
            ),
        ),
    ]
