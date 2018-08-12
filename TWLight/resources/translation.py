from modeltranslation.translator import translator, TranslationOptions

from .models import Partner, Stream, TextFieldTag

# See https://django-modeltranslation.readthedocs.io/en/latest/registration.html
class PartnerTranslationOptions(TranslationOptions):
    fields = ('description', 'send_instructions', 'short_description')

translator.register(Partner, PartnerTranslationOptions)

class StreamTranslationOptions(TranslationOptions):
    fields = ('description',)

translator.register(Stream, StreamTranslationOptions)


class MultilingualTagTO(TranslationOptions):
    fields = ('name',)
    # This setting lets name be nullable in the database. This is important
    # because unique=True for name, and an empty CharField is normally not
    # nullable so it is stored as ''; this means two empty CharFields violate
    # the uniqueness constraint, which means if we try to save more than one
    # tag without full translations we will be sad.
    empty_values = {'name': None}

translator.register(TextFieldTag, MultilingualTagTO)
