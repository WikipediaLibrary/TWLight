from modeltranslation.translator import translator, TranslationOptions
from taggit.models import Tag

from .models import Partner, Stream

# See https://django-modeltranslation.readthedocs.io/en/latest/registration.html
class PartnerTranslationOptions(TranslationOptions):
    fields = ('description', 'send_instructions')

translator.register(Partner, PartnerTranslationOptions)

class StreamTranslationOptions(TranslationOptions):
    fields = ('description',)

translator.register(Stream, StreamTranslationOptions)


class MultilingualTagTO(TranslationOptions):
    fields = ('name',)
    # This setting lets name be nullable in the database. This is important
    # because unique=True for name, and an empty CharField is normally not
    # nullable so it is stored as ''; this means two empty CharFields violate
    # the uniqueness constraint, which means if we try to save more than on
    # tag without full translations we will be sad.
    empty_values = {'name': None}

translator.register(Tag, MultilingualTagTO)
