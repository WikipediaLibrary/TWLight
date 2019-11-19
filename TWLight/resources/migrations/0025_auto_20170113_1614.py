# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0024_auto_20170113_1606")]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="description",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_en",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_fi",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="description_fr",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="languages",
            field=models.ManyToManyField(
                help_text="Select all languages in which this partner publishes content.",
                to="resources.Language",
                null=True,
                blank=True,
            ),
        ),
    ]
