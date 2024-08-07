# Generated by Django 4.2.14 on 2024-07-24 14:10

import TWLight.resources.models
from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [
        ("resources", "0064_auto_20210201_1612"),
        ("resources", "0065_auto_20210215_1404"),
        ("resources", "0066_auto_20210420_1927"),
        ("resources", "0067_remove_partner_old_tags"),
        ("resources", "0068_partner_new_tags"),
        ("resources", "0069_auto_20210503_1809"),
        ("resources", "0070_auto_20210505_2158"),
        ("resources", "0071_remove_tags_field_models"),
        ("resources", "0072_stream_description_lv"),
        ("resources", "0073_stream_description_it"),
    ]

    dependencies = [
        ("resources", "0063_auto_20190220_1639_squashed_0084_auto_20201019_1310"),
    ]

    operations = [
        migrations.AlterField(
            model_name="partner",
            name="date_created",
            field=models.DateField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="stream",
            name="description_he",
            field=models.TextField(
                blank=True,
                help_text="Optional description of this stream's resources.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="textfieldtag",
            name="name_he",
            field=models.TextField(max_length=100, null=True, verbose_name="Name"),
        ),
        migrations.AlterField(
            model_name="language",
            name="language",
            field=models.CharField(
                choices=[
                    ("af", "Afrikaans"),
                    ("ar", "العربية"),
                    ("ast", "asturianu"),
                    ("az", "az-latn"),
                    ("be", "беларуская"),
                    ("bg", "български"),
                    ("bn", "বাংলা"),
                    ("br", "brezhoneg"),
                    ("bs", "bosanski"),
                    ("ca", "català"),
                    ("cs", "čeština"),
                    ("cy", "Cymraeg"),
                    ("da", "dansk"),
                    ("de", "Deutsch"),
                    ("dsb", "dolnoserbski"),
                    ("el", "Ελληνικά"),
                    ("en", "English"),
                    ("en-gb", "British English"),
                    ("eo", "Esperanto"),
                    ("es", "español"),
                    ("es-ni", "español nicaragüense"),
                    ("et", "eesti"),
                    ("eu", "euskara"),
                    ("fa", "فارسی"),
                    ("fi", "suomi"),
                    ("fr", "français"),
                    ("fy", "Frysk"),
                    ("ga", "Gaeilge"),
                    ("gd", "Gàidhlig"),
                    ("gl", "galego"),
                    ("he", "עברית"),
                    ("hi", "हिन्दी"),
                    ("hr", "hrvatski"),
                    ("hsb", "hornjoserbsce"),
                    ("hu", "magyar"),
                    ("hy", "Հայերեն"),
                    ("ia", "interlingua"),
                    ("id", "Bahasa Indonesia"),
                    ("ig", "Igbo"),
                    ("io", "Ido"),
                    ("is", "íslenska"),
                    ("it", "italiano"),
                    ("ja", "日本語"),
                    ("ka", "ქართული"),
                    ("kab", "Taqbaylit"),
                    ("kk", "kk-cyrl"),
                    ("km", "ភាសាខ្មែរ"),
                    ("kn", "ಕನ್ನಡ"),
                    ("ko", "한국어"),
                    ("ky", "Кыргызча"),
                    ("lb", "Lëtzebuergesch"),
                    ("lt", "lietuvių"),
                    ("lv", "latviešu"),
                    ("mk", "македонски"),
                    ("ml", "മലയാളം"),
                    ("mn", "монгол"),
                    ("mr", "मराठी"),
                    ("my", "မြန်မာဘာသာ"),
                    ("nb", "norsk (bokmål)"),
                    ("ne", "नेपाली"),
                    ("nl", "Nederlands"),
                    ("nn", "norsk (nynorsk)"),
                    ("os", "Ирон"),
                    ("pa", "pa-guru"),
                    ("pl", "polski"),
                    ("pt", "português"),
                    ("pt-br", "português do Brasil"),
                    ("ro", "română"),
                    ("ru", "русский"),
                    ("sk", "slovenčina"),
                    ("sl", "slovenščina"),
                    ("sq", "shqip"),
                    ("sr", "sr-cyrl"),
                    ("sr-latn", "srpski"),
                    ("sv", "svenska"),
                    ("sw", "Kiswahili"),
                    ("ta", "தமிழ்"),
                    ("te", "తెలుగు"),
                    ("tg", "tg-cyrl"),
                    ("th", "ไทย"),
                    ("tk", "Türkmençe"),
                    ("tr", "Türkçe"),
                    ("tt", "татарча"),
                    ("udm", "удмурт"),
                    ("uk", "українська"),
                    ("ur", "اردو"),
                    ("uz", "oʻzbekcha"),
                    ("vi", "Tiếng Việt"),
                    ("zh-hans", "中文（简体）"),
                    ("zh-hant", "中文（繁體）"),
                ],
                max_length=8,
                unique=True,
                validators=[TWLight.resources.models.validate_language_code],
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="mutually_exclusive",
            field=models.BooleanField(
                blank=True,
                default=None,
                help_text="If True, users can only apply for one Stream at a time from this Partner. If False, users can apply for multiple Streams at a time. This field must be filled in when Partners have multiple Streams, but may be left blank otherwise.",
                null=True,
            ),
        ),
        migrations.RemoveField(
            model_name="partner",
            name="old_tags",
        ),
        migrations.AddField(
            model_name="partner",
            name="new_tags",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ar",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_br",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_da",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_de",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_en",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_en_gb",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_eo",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_es",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_fa",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_fi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_fr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_hi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ind",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ja",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ko",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_mk",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_mr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_my",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_pl",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_pt",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_pt_br",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ro",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ru",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_sv",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_ta",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_tr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_uk",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_vi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_zh_hans",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="description_zh_hant",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ar",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_br",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_da",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_de",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_en",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_en_gb",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_eo",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_es",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_fa",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_fi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_fr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_hi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ind",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ja",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ko",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_mk",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_mr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_my",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_pl",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_pt",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_pt_br",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ro",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ru",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_sv",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_ta",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_tr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_uk",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_vi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_zh_hans",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="send_instructions_zh_hant",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ar",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_br",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_da",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_de",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_en",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_en_gb",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_eo",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_es",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_fa",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_fi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_fr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_hi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ind",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ja",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ko",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_mk",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_mr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_my",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_pl",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_pt",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_pt_br",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ro",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ru",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_sv",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_ta",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_tr",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_uk",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_vi",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_zh_hans",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="short_description_zh_hant",
        ),
        migrations.RemoveField(
            model_name="partner",
            name="tags",
        ),
        migrations.DeleteModel(
            name="TaggedTextField",
        ),
        migrations.DeleteModel(
            name="TextFieldTag",
        ),
        migrations.AddField(
            model_name="stream",
            name="description_lv",
            field=models.TextField(
                blank=True,
                help_text="Optional description of this stream's resources.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="stream",
            name="description_it",
            field=models.TextField(
                blank=True,
                help_text="Optional description of this stream's resources.",
                null=True,
            ),
        ),
    ]
