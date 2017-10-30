# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import durationfield.db.models.fields.duration
import datetime
from django.utils.timezone import utc
from django.conf import settings
import TWLight.resources.models
import taggit.managers


def copy_access_grant_terms(apps, schema_editor):
    Partner = apps.get_model('resources', 'Partner')
    # Although this looks like it should only get AVAILABLE Partners (since
    # we've defined a custom manager), in fact it uses the Django default
    # internal manager and finds all Partners.
    for partner in Partner.objects.all():
        partner.access_grant_term_pythonic = partner.access_grant_term
        partner.save()


def delete_access_grant_terms(apps, schema_editor):
    Partner = apps.get_model('resources', 'Partner')
    for partner in Partner.objects.all():
        partner.access_grant_term_pythonic = None
        partner.save()


def fix_partner_status(apps, schema_editor):
    Partner = apps.get_model("resources", "Partner")
    for partner in Partner.objects.all():
        # This should be Partner.AVAILABLE. We can't reference that directly
        # since it's not available to the migrations, though. Careful!
        partner.status = 0
        partner.save()

def initialize_languages(apps, schema_editor):
    """
    Make sure the database starts with a few languages we know Partners offer.
    (This will also make it easier for administrators to use the language
    field in the admin site.)
    """
    Language = apps.get_model("resources", "Language")
    basic_codes = ['en', 'fr', 'fa']
    for code in basic_codes:
        lang = Language(language=code)
        lang.save()

class Migration(migrations.Migration):

    replaces = [(b'resources', '0001_initial'), (b'resources', '0002_auto_20160324_1826'), (b'resources', '0003_partner_access_grant_term'), (b'resources', '0004_auto_20160509_1817'), (b'resources', '0005_partner_date_created'), (b'resources', '0006_auto_20160706_1409'), (b'resources', '0007_auto_20160721_1750'), (b'resources', '0008_auto_20160908_1410'), (b'resources', '0009_auto_20160930_1434'), (b'resources', '0010_auto_20161024_1942'), (b'resources', '0011_auto_20161027_1836'), (b'resources', '0012_partner_status'), (b'resources', '0013_auto_20161207_1505'), (b'resources', '0014_auto_20161208_1520'), (b'resources', '0015_auto_20161208_1526'), (b'resources', '0016_stream_languages'), (b'resources', '0017_auto_20161208_1940'), (b'resources', '0018_auto_20161213_1603'), (b'resources', '0019_auto_20161216_1650'), (b'resources', '0020_move_to_internal_durationfield'), (b'resources', '0021_auto_20161216_1702'), (b'resources', '0022_auto_20161216_1704'), (b'resources', '0023_auto_20161217_1717'), (b'resources', '0024_auto_20170113_1606'), (b'resources', '0025_auto_20170113_1614'), (b'resources', '0026_partner_coordinator'), (b'resources', '0027_auto_20170117_2046'), (b'resources', '0028_auto_20170126_2225'), (b'resources', '0029_partner_tags'), (b'resources', '0030_auto_20170203_1620'), (b'resources', '0031_partner_renewals_available'), (b'resources', '0032_auto_20170611_1344'), (b'resources', '0033_auto_20170621_0822'), (b'resources', '0034_auto_20170624_1554'), (b'resources', '0035_partner_send_instructions'), (b'resources', '0036_auto_20170716_1235')]

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'Organizational role or job title. This is NOT intended to be used for honorofics.', max_length=30)),
                ('email', models.EmailField(max_length=75)),
                ('full_name', models.CharField(max_length=50)),
                ('short_name', models.CharField(help_text=b"The form of the contact person's name to use in email greetings (as in 'Hi Jake')", max_length=15)),
            ],
        ),
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('company_name', models.CharField(help_text=b"Partner organization's name (e.g. McFarland). Note: this will be user-visible and *not translated*.", max_length=30)),
                ('terms_of_use', models.URLField(help_text=b'Required if this company requires that users agree to terms of use as a condition of applying for access; optional otherwise.', null=True, blank=True)),
                ('description', models.TextField(help_text=b"Optional description of this partner's offerings.", null=True, blank=True)),
                ('mutually_exclusive', models.NullBooleanField(default=None, help_text=b'If True, users can only apply for one Stream at a time from this Partner. If False, users can apply for multiple Streams at a time. This field must be filled in when Partners have multiple Streams, but may be left blank otherwise.')),
                ('real_name', models.BooleanField(default=False)),
                ('country_of_residence', models.BooleanField(default=False)),
                ('specific_title', models.BooleanField(default=False)),
                ('specific_stream', models.BooleanField(default=False)),
                ('occupation', models.BooleanField(default=False)),
                ('affiliation', models.BooleanField(default=False)),
                ('agreement_with_terms_of_use', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b"Name of stream (e.g. 'Health and Behavioral Sciences). Will be user-visible and *not translated*. Do not include the name of the partner here. If partner name and resource name need to be presented together, templates are responsible for presenting them in a format that can be internationalized.", max_length=50)),
                ('description', models.TextField(help_text=b"Optional description of this stream's contents.", null=True, blank=True)),
                ('partner', models.ForeignKey(related_name='streams', to='resources.Partner')),
            ],
        ),
        migrations.AddField(
            model_name='contact',
            name='partner',
            field=models.ForeignKey(related_name='contacts', to='resources.Partner'),
        ),
        migrations.AddField(
            model_name='partner',
            name='access_grant_term',
            field=durationfield.db.models.fields.duration.DurationField(help_text=b"The standard length of an access grant from this Partner. Enter like '365 days' or '365d' or '1 year'.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='date_created',
            field=models.DateField(default=datetime.datetime(2016, 5, 9, 19, 18, 3, 475335, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='contact',
            options={'verbose_name': 'contact person', 'verbose_name_plural': 'contact people'},
        ),
        migrations.AlterModelOptions(
            name='partner',
            options={'verbose_name': 'partner', 'verbose_name_plural': 'partners'},
        ),
        migrations.AlterModelOptions(
            name='stream',
            options={'verbose_name': 'collection', 'verbose_name_plural': 'collections'},
        ),
        migrations.AddField(
            model_name='partner',
            name='logo_url',
            field=models.URLField(help_text='Optional URL of an image that can be used to represent this partner.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='affiliation',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify their institutional affiliation.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='agreement_with_terms_of_use',
            field=models.BooleanField(default=False, help_text="Mark as true if this partner requires applicants to agree with the partner's terms of use."),
        ),
        migrations.AlterField(
            model_name='partner',
            name='country_of_residence',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify their countries of residence.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='occupation',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify their occupation.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='real_name',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify their real names.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='specific_stream',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify a particular database they want to access.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='specific_title',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify a particular title they want to access.'),
        ),
        migrations.AlterModelOptions(
            name='partner',
            options={'ordering': ['company_name'], 'verbose_name': 'partner', 'verbose_name_plural': 'partners'},
        ),
        migrations.AlterModelOptions(
            name='stream',
            options={'ordering': ['partner', 'name'], 'verbose_name': 'collection', 'verbose_name_plural': 'collections'},
        ),
        migrations.AlterField(
            model_name='partner',
            name='terms_of_use',
            field=models.URLField(help_text='Link to terms of use. Required if this company requires that users agree to terms of use as a condition of applying for access; optional otherwise.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(help_text='Organizational role or job title. This is NOT intended to be used for honorifics like Mr., Ms., Mx., etc.', max_length=30),
        ),
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(help_text='Organizational role or job title. This is NOT intended to be used for honorifics.', max_length=30),
        ),
        migrations.AlterField(
            model_name='partner',
            name='company_name',
            field=models.CharField(help_text="Partner organization's name (e.g. McFarland). Note: this will be user-visible and *not translated*.", max_length=40),
        ),
        migrations.AddField(
            model_name='partner',
            name='status',
            field=models.IntegerField(default=1, choices=[(0, 'Available'), (1, 'Not available')]),
        ),
        migrations.RunPython(
            code=fix_partner_status,
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(max_length=8, choices=[(b'af', b'Afrikaans'), (b'ar', b'Arabic'), (b'ast', b'Asturian'), (b'az', b'Azerbaijani'), (b'bg', b'Bulgarian'), (b'be', b'Belarusian'), (b'bn', b'Bengali'), (b'br', b'Breton'), (b'bs', b'Bosnian'), (b'ca', b'Catalan'), (b'cs', b'Czech'), (b'cy', b'Welsh'), (b'da', b'Danish'), (b'de', b'German'), (b'el', b'Greek'), (b'en', b'English'), (b'en-au', b'Australian English'), (b'en-gb', b'British English'), (b'eo', b'Esperanto'), (b'es', b'Spanish'), (b'es-ar', b'Argentinian Spanish'), (b'es-mx', b'Mexican Spanish'), (b'es-ni', b'Nicaraguan Spanish'), (b'es-ve', b'Venezuelan Spanish'), (b'et', b'Estonian'), (b'eu', b'Basque'), (b'fa', b'Persian'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fy', b'Frisian'), (b'ga', b'Irish'), (b'gl', b'Galician'), (b'he', b'Hebrew'), (b'hi', b'Hindi'), (b'hr', b'Croatian'), (b'hu', b'Hungarian'), (b'ia', b'Interlingua'), (b'id', b'Indonesian'), (b'io', b'Ido'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'ja', b'Japanese'), (b'ka', b'Georgian'), (b'kk', b'Kazakh'), (b'km', b'Khmer'), (b'kn', b'Kannada'), (b'ko', b'Korean'), (b'lb', b'Luxembourgish'), (b'lt', b'Lithuanian'), (b'lv', b'Latvian'), (b'mk', b'Macedonian'), (b'ml', b'Malayalam'), (b'mn', b'Mongolian'), (b'mr', b'Marathi'), (b'my', b'Burmese'), (b'nb', b'Norwegian Bokmal'), (b'ne', b'Nepali'), (b'nl', b'Dutch'), (b'nn', b'Norwegian Nynorsk'), (b'os', b'Ossetic'), (b'pa', b'Punjabi'), (b'pl', b'Polish'), (b'pt', b'Portuguese'), (b'pt-br', b'Brazilian Portuguese'), (b'ro', b'Romanian'), (b'ru', b'Russian'), (b'sk', b'Slovak'), (b'sl', b'Slovenian'), (b'sq', b'Albanian'), (b'sr', b'Serbian'), (b'sr-latn', b'Serbian Latin'), (b'sv', b'Swedish'), (b'sw', b'Swahili'), (b'ta', b'Tamil'), (b'te', b'Telugu'), (b'th', b'Thai'), (b'tr', b'Turkish'), (b'tt', b'Tatar'), (b'udm', b'Udmurt'), (b'uk', b'Ukrainian'), (b'ur', b'Urdu'), (b'vi', b'Vietnamese'), (b'zh-cn', b'Simplified Chinese'), (b'zh-hans', b'Simplified Chinese'), (b'zh-hant', b'Traditional Chinese'), (b'zh-tw', b'Traditional Chinese')], error_messages={b'invalid_choice': 'You must enter an ISO language code, as in the LANGUAGES setting at https://github.com/django/django/blob/master/django/conf/global_settings.py'})),
            ],
            options={
                'verbose_name': 'Language',
                'verbose_name_plural': 'Languages',
            },
        ),
        migrations.AddField(
            model_name='partner',
            name='languages',
            field=models.ManyToManyField(to=b'resources.Language', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='status',
            field=models.IntegerField(default=1, help_text='Should this Partner be displayed to end users? Is it open for applications right now?', choices=[(0, 'Available'), (1, 'Not available')]),
        ),
        migrations.RunPython(
            code=initialize_languages,
        ),
        migrations.AddField(
            model_name='stream',
            name='languages',
            field=models.ManyToManyField(to=b'resources.Language', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='language',
            name='language',
            field=models.CharField(max_length=8, unique=True, choices=[(b'af', b'Afrikaans'), (b'ar', b'Arabic'), (b'ast', b'Asturian'), (b'az', b'Azerbaijani'), (b'bg', b'Bulgarian'), (b'be', b'Belarusian'), (b'bn', b'Bengali'), (b'br', b'Breton'), (b'bs', b'Bosnian'), (b'ca', b'Catalan'), (b'cs', b'Czech'), (b'cy', b'Welsh'), (b'da', b'Danish'), (b'de', b'German'), (b'el', b'Greek'), (b'en', b'English'), (b'en-au', b'Australian English'), (b'en-gb', b'British English'), (b'eo', b'Esperanto'), (b'es', b'Spanish'), (b'es-ar', b'Argentinian Spanish'), (b'es-mx', b'Mexican Spanish'), (b'es-ni', b'Nicaraguan Spanish'), (b'es-ve', b'Venezuelan Spanish'), (b'et', b'Estonian'), (b'eu', b'Basque'), (b'fa', b'Persian'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fy', b'Frisian'), (b'ga', b'Irish'), (b'gl', b'Galician'), (b'he', b'Hebrew'), (b'hi', b'Hindi'), (b'hr', b'Croatian'), (b'hu', b'Hungarian'), (b'ia', b'Interlingua'), (b'id', b'Indonesian'), (b'io', b'Ido'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'ja', b'Japanese'), (b'ka', b'Georgian'), (b'kk', b'Kazakh'), (b'km', b'Khmer'), (b'kn', b'Kannada'), (b'ko', b'Korean'), (b'lb', b'Luxembourgish'), (b'lt', b'Lithuanian'), (b'lv', b'Latvian'), (b'mk', b'Macedonian'), (b'ml', b'Malayalam'), (b'mn', b'Mongolian'), (b'mr', b'Marathi'), (b'my', b'Burmese'), (b'nb', b'Norwegian Bokmal'), (b'ne', b'Nepali'), (b'nl', b'Dutch'), (b'nn', b'Norwegian Nynorsk'), (b'os', b'Ossetic'), (b'pa', b'Punjabi'), (b'pl', b'Polish'), (b'pt', b'Portuguese'), (b'pt-br', b'Brazilian Portuguese'), (b'ro', b'Romanian'), (b'ru', b'Russian'), (b'sk', b'Slovak'), (b'sl', b'Slovenian'), (b'sq', b'Albanian'), (b'sr', b'Serbian'), (b'sr-latn', b'Serbian Latin'), (b'sv', b'Swedish'), (b'sw', b'Swahili'), (b'ta', b'Tamil'), (b'te', b'Telugu'), (b'th', b'Thai'), (b'tr', b'Turkish'), (b'tt', b'Tatar'), (b'udm', b'Udmurt'), (b'uk', b'Ukrainian'), (b'ur', b'Urdu'), (b'vi', b'Vietnamese'), (b'zh-cn', b'Simplified Chinese'), (b'zh-hans', b'Simplified Chinese'), (b'zh-hant', b'Traditional Chinese'), (b'zh-tw', b'Traditional Chinese')], validators=[TWLight.resources.models.validate_language_code]),
        ),
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(help_text="Organizational role or job title. This is NOT intended to be used for honorifics. Think 'Director of Editorial Services', not 'Ms.'", max_length=75),
        ),
        migrations.AddField(
            model_name='partner',
            name='access_grant_term_pythonic',
            field=models.DurationField(default=datetime.timedelta(365), null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.RunPython(
            code=copy_access_grant_terms,
            reverse_code=delete_access_grant_terms,
        ),
        migrations.RemoveField(
            model_name='partner',
            name='access_grant_term',
        ),
        migrations.RenameField(
            model_name='partner',
            old_name='access_grant_term_pythonic',
            new_name='access_grant_term',
        ),
        migrations.AlterField(
            model_name='partner',
            name='access_grant_term',
            field=models.DurationField(default=datetime.timedelta(365), help_text='The standard length of an access grant from this Partner. Entered as <days hours:minutes:seconds>. Defaults to 365 days.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='description',
            field=models.TextField(help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='stream',
            name='description',
            field=models.TextField(help_text="Optional description of this stream's contents. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='description_en',
            field=models.TextField(help_text="Optional description of this partner's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='description_fi',
            field=models.TextField(help_text="Optional description of this partner's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='description_fr',
            field=models.TextField(help_text="Optional description of this partner's resources.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='description',
            field=models.TextField(help_text="Optional description of this partner's offerings. You can enter HTML and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='languages',
            field=models.ManyToManyField(help_text='Select all languages in which this partner publishes content.', to=b'resources.Language', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='coordinator',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The coordinator for this Partner, if any.', null=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='languages',
            field=models.ManyToManyField(help_text='Select all languages in which this partner publishes content.', to=b'resources.Language', blank=True),
        ),
        migrations.AlterField(
            model_name='stream',
            name='languages',
            field=models.ManyToManyField(to=b'resources.Language', blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='status',
            field=models.IntegerField(default=1, help_text='Should this Partner be displayed to end users? Is it open for applications right now?', choices=[(0, 'Available'), (1, 'Not available'), (2, 'Waitlisted')]),
        ),
        migrations.AddField(
            model_name='partner',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='partner',
            name='renewals_available',
            field=models.BooleanField(default=False, help_text='Can access grants to this partner be renewed? If so, users will be able to request renewals when their access is close to expiring.'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='title',
            field=models.CharField(help_text="Organizational role or job title. This is NOT intended to be used for honorifics. Think 'Director of Editorial Services', not 'Ms.' Optional.", max_length=75, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='description',
            field=models.TextField(help_text="Optional description of this partner's offerings. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template. Whatever you enter here will also be automatically copied over to the description field for *your current language*, so you do not need to also fill that out.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='stream',
            name='description',
            field=models.TextField(help_text="Optional description of this stream's contents. You can enter wikicode and it should render properly - if it does not, the developer forgot a | safe filter in the template.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='company_name',
            field=models.CharField(help_text="Partner's name (e.g. McFarland). Note: this will be user-visible and *not translated*.", max_length=40),
        ),
        migrations.AlterField(
            model_name='partner',
            name='country_of_residence',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicant countries of residence.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='description',
            field=models.TextField(help_text="Optional description of this partner's resources.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partner',
            name='real_name',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicant names.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='specific_stream',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify the database they want to access.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='specific_title',
            field=models.BooleanField(default=False, help_text='Mark as true if this partner requires applicants to specify the title they want to access.'),
        ),
        migrations.AlterField(
            model_name='partner',
            name='terms_of_use',
            field=models.URLField(help_text='Link to terms of use. Required if users must agree to terms of use to get access; optional otherwise.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='stream',
            name='description',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='stream',
            name='name',
            field=models.CharField(help_text="Name of stream (e.g. 'Health and Behavioral Sciences). Will be user-visible and *not translated*. Do not include the name of the partner here.", max_length=50),
        ),
        migrations.AddField(
            model_name='stream',
            name='description_en',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='stream',
            name='description_fi',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='stream',
            name='description_fr',
            field=models.TextField(help_text="Optional description of this stream's resources.", null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='send_instructions',
            field=models.TextField(help_text='Optional instructions for sending application data to this partner.', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='send_instructions_en',
            field=models.TextField(help_text='Optional instructions for sending application data to this partner.', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='send_instructions_fi',
            field=models.TextField(help_text='Optional instructions for sending application data to this partner.', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partner',
            name='send_instructions_fr',
            field=models.TextField(help_text='Optional instructions for sending application data to this partner.', null=True, blank=True),
        ),
    ]
