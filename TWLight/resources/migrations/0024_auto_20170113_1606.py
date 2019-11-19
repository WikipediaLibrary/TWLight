# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("resources", "0023_auto_20161217_1717")]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="description_en",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="description_fi",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.",
                null=True,
                blank=True,
            ),
        ),
        migrations.AddField(
            model_name="partner",
            name="description_fr",
            field=models.TextField(
                help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.",
                null=True,
                blank=True,
            ),
        ),
    ]
