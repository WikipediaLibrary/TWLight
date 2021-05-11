from modeltranslation.translator import translator, TranslationOptions

from .models import Stream

# See https://django-modeltranslation.readthedocs.io/en/latest/registration.html


class StreamTranslationOptions(TranslationOptions):
    fields = ("description",)


translator.register(Stream, StreamTranslationOptions)


# Temporary fix for a bug in modeltranslation. See
# https://github.com/deschler/django-modeltranslation/issues/455
# Should be removed as soon as bug is resolved

Stream._meta.base_manager_name = None
