from django import forms
from django.contrib import admin
from TWLight.users.groups import get_coordinators

from .models import Partner, PartnerLogo, Stream, Contact, Language


class LanguageAdmin(admin.ModelAdmin):
    search_fields = ('language',)
    list_display = ('language',)

admin.site.register(Language, LanguageAdmin)


class PartnerLogoInline(admin.TabularInline):
    model = PartnerLogo


class PartnerAdmin(admin.ModelAdmin):
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


    search_fields = ('company_name',)
    list_display = ('company_name', 'description', 'id', 'get_languages')
    inlines = [PartnerLogoInline]

admin.site.register(Partner, PartnerAdmin)



class StreamAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'name',)
    list_display = ('id', 'partner', 'name', 'description', 'get_languages')

admin.site.register(Stream, StreamAdmin)



class ContactAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'full_name', 'short_name',)
    list_display = ('id', 'title', 'full_name', 'partner', 'email',)

admin.site.register(Contact, ContactAdmin)
