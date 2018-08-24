from django import forms
from django.contrib import admin
from modeltranslation.admin import TabbedExternalJqueryTranslationAdmin
from TWLight.users.groups import get_coordinators

from .models import TextFieldTag, Partner, PartnerLogo, Stream, Contact, Language, Video, AccessCode
from .models import TextFieldTag, Partner, PartnerLogo, Stream, Contact, Language, AccessCode


class LanguageAdmin(admin.ModelAdmin):
    search_fields = ('language',)
    list_display = ('language',)

admin.site.register(Language, LanguageAdmin)


class TextFieldTagAdmin(TabbedExternalJqueryTranslationAdmin):
    model = TextFieldTag
    search_fields = ('name',)
    list_display = ('name', 'slug')

    def has_add_permission(self, request):
        """
        Adding tags directly through the Resources > Tags admin screen exposes
        the fact that tag model has name unique == False, allowing admins to
        create tags with duplicate names, but different slugs. Adding them from
        the resources > Partner/Stream screen does not have this problem. Thus,
        this hack.
        """
        return False

admin.site.register(TextFieldTag, TextFieldTagAdmin)


class PartnerLogoInline(admin.TabularInline):
    model = PartnerLogo


class PartnerAdmin(TabbedExternalJqueryTranslationAdmin):
    class CustomModelChoiceField(forms.ModelChoiceField):
        """
        This lets us relabel the users in the dropdown with their recognizable
        wikipedia usernames, rather than their cryptic local IDs. It should be
        used only for the coordinator field.
        """

        def label_from_instance(self, obj):
            return '{editor.wp_username}'.format(
                editor=obj.editor)


    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        The coordinator dropdown should limit choices to actual coordinators,
        for admin ease of use.
        """
        if db_field.name == "coordinator":
            return self.CustomModelChoiceField(
                queryset=get_coordinators().user_set.all(),
                required=False)
        return super(PartnerAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    def language_strings(self, object):
        return [str(lang) for lang in object.languages.all()]
    language_strings.short_description = "Languages"

    search_fields = ('company_name',)
    list_display = ('company_name', 'short_description', 'id', 'language_strings')
    inlines = [PartnerLogoInline]

admin.site.register(Partner, PartnerAdmin)



class StreamAdmin(TabbedExternalJqueryTranslationAdmin):
    search_fields = ('partner__company_name', 'name',)
    list_display = ('id', 'partner', 'name', 'description', 'get_languages')

admin.site.register(Stream, StreamAdmin)



class ContactAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'full_name', 'short_name',)
    list_display = ('id', 'title', 'full_name', 'partner', 'email',)

admin.site.register(Contact, ContactAdmin)



class VideoAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'tutorial_video_url',)
    list_display = ('partner', 'tutorial_video_url', 'id',)

admin.site.register(Video, VideoAdmin)



class AccessCodeAdmin(admin.ModelAdmin):
    search_fields = ('code', 'partner', 'application',)
    list_display = ('code', 'partner', 'application',)

admin.site.register(AccessCode, AccessCodeAdmin)
