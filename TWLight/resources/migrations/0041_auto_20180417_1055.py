# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0040_partner_featured")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="account_email",
            field=models.BooleanField(
                default=False,
                help_text="Mark as true if this partner requires applicants to have already signed up at the partner website.",
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="registration_url",
            field=models.URLField(
                help_text="Link to registration page. Required if users must sign up on the partner's website in advance; optional otherwise.",
                null=True,
                blank=True,
            ),
        ),
    ]
