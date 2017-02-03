from modeltranslation.translator import translator, TranslationOptions
from taggit.models import Tag

from .models import Partner

# See https://django-modeltranslation.readthedocs.io/en/latest/registration.html
class PartnerTranslationOptions(TranslationOptions):
    fields = ('description',)

translator.register(Partner, PartnerTranslationOptions)



class TagTranslationTranslations(TranslationOptions):
    fields = ('name',)

translator.register(Tag, TagTranslationTranslations)
