from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from .factories import PartnerFactory, StreamFactory
from .models import Language, RESOURCE_LANGUAGES

class LanguageModelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        """
        The uniqueness constraint on Language.language can cause tests to fail
        due to IntegrityErrors as we try to create new languages unless we are
        careful, so let's use get_or_create, not create. (The Django database
        truncation that runs between tests isn't sufficient, since it drops the
        primary key but doesn't delete the fields.)
        """
        cls.lang_en, _ = Language.objects.get_or_create(language='en')
        cls.lang_fr, _ = Language.objects.get_or_create(language='fr')


    def test_validation(self):
        # Note that RESOURCE_LANGUAGES is a list of tuples, such as
        # `('en', 'English')`, but we only care about the first element of each
        # tuple, as it is the one stored in the database.
        language_codes = [lang[0] for lang in RESOURCE_LANGUAGES]

        not_a_language = 'fksdja'
        assert not_a_language not in language_codes
        bad_lang = Language(language=not_a_language)
        with self.assertRaises(ValidationError):
            bad_lang.save()


    def test_language_display(self):
        self.assertEqual(self.lang_en.__unicode__(), 'English')


    def test_language_uniqueness(self):
        with self.assertRaises(IntegrityError):
            lang = Language(language='en')
            lang.save()



class PartnerModelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.lang_en, _ = Language.objects.get_or_create(language='en')
        cls.lang_fr, _ = Language.objects.get_or_create(language='fr')


    def test_get_languages(self):
        partner = PartnerFactory()

        # At first, the list of languages should be empty.
        self.assertFalse(partner.languages.all())

        partner.languages.add(self.lang_en)
        self.assertEqual(partner.get_languages, u'English')

        # Order isn't important.
        partner.languages.add(self.lang_fr)
        self.assertIn(partner.get_languages,
            [u'English, French', u'French, English'])



class StreamModelTests(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.lang_en, _ = Language.objects.get_or_create(language='en')
        cls.lang_fr, _ = Language.objects.get_or_create(language='fr')


    def test_get_languages(self):
        stream = StreamFactory()

        # At first, the list of languages should be empty.
        self.assertFalse(stream.languages.all())

        stream.languages.add(self.lang_en)
        self.assertEqual(stream.get_languages, u'English')

        # Order isn't important.
        stream.languages.add(self.lang_fr)
        self.assertIn(stream.get_languages,
            [u'English, French', u'French, English'])
