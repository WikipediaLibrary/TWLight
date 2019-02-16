from modeltranslation.translator import translator, TranslationOptions

from .models import Partner, Stream, TextFieldTag

# See https://django-modeltranslation.readthedocs.io/en/latest/registration.html
class PartnerTranslationOptions(TranslationOptions):
    fields = ('send_instructions',)

translator.register(Partner, PartnerTranslationOptions)


class MultilingualTagTO(TranslationOptions):
    fields = ('name',)
    # This setting lets name be nullable in the database. This is important
    # because unique=True for name, and an empty CharField is normally not
    # nullable so it is stored as ''; this means two empty CharFields violate
    # the uniqueness constraint, which means if we try to save more than one
    # tag without full translations we will be sad.
    empty_values = {'name': None}

translator.register(TextFieldTag, MultilingualTagTO)


# Temporary fix for a bug in modeltranslation. See
# https://github.com/deschler/django-modeltranslation/issues/455
# Should be removed as soon as bug is resolved

Partner._meta.base_manager_name = None
Stream._meta.base_manager_name = None
TextFieldTag._meta.base_manager_name = None
