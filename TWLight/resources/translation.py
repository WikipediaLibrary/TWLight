from modeltranslation.translator import translator, TranslationOptions
from .models import Partner

# See https://django-modeltranslation.readthedocs.io/en/latest/registration.html
class PartnerTranslationOptions(TranslationOptions):
    fields = ('description',)

translator.register(Partner, PartnerTranslationOptions)
