# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0031_partner_renewals_available")]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="title",
            field=models.CharField(
                help_text="Organizational role or job title. This is NOT intended to be used for honorifics. Think 'Director of Editorial Services', not 'Ms.' Optional.",
                max_length=75,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_en",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_fi",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_fr",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="stream",
            name="description",
            field=models.TextField(
                help_text="Optional description of this stream's contents. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template.",
                null=True,
                blank=True,
            ),
        ),
    ]
