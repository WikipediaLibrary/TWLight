from django.contrib import messages
from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import ugettext as _
from modeltranslation.admin import TabbedExternalJqueryTranslationAdmin

from TWLight.users.groups import get_coordinators

from .models import TextFieldTag, Partner, PartnerLogo, Stream, Contact, Language, Video, Suggestion, AccessCode

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

class ContactInline(admin.TabularInline):
    model = Contact

class VideoInline(admin.TabularInline):
    model = Video

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
    list_display = ('company_name', 'id', 'language_strings')
    inlines = [ContactInline, VideoInline, PartnerLogoInline]

admin.site.register(Partner, PartnerAdmin)



class StreamAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'name',)
    list_display = ('id', 'partner', 'name', 'get_languages')

admin.site.register(Stream, StreamAdmin)


class SuggestionAdmin(admin.ModelAdmin):
    search_fields = ('suggested_company_name',)
    list_display = ('suggested_company_name', 'description', 'id',)
    
admin.site.register(Suggestion, SuggestionAdmin)


class ContactAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'full_name', 'short_name',)
    list_display = ('id', 'title', 'full_name', 'partner', 'email',)

admin.site.register(Contact, ContactAdmin)


class VideoAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'tutorial_video_url',)
    list_display = ('partner', 'tutorial_video_url', 'id',)

admin.site.register(Video, VideoAdmin)


class AccessCodeAdmin(admin.ModelAdmin):
    search_fields = ('code', 'partner', 'authorization',)
    list_display = ('code', 'partner', 'authorization',)
    raw_id_fields = ('authorization',)

    change_list_template = 'accesscode_changelist.html'

    def get_urls(self):
        urls = super(AccessCodeAdmin, self).get_urls()
        my_urls = [
            url('import/', self.import_csv),
            ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            uploaded_csv = request.FILES['access_code_csv']
            return_url = HttpResponseRedirect("..")

            if not uploaded_csv.name.endswith('.csv'):
                # Translators: When staff upload a file containing access codes, it must be a .csv file. This error message is shown if it is any other file type.
                messages.error(request, _('File must be a csv'))
                return return_url

            # Check against the maximum upload size (2.5mb by default)
            if uploaded_csv.multiple_chunks():
                # Translators: When staff upload a file containing access codes, they receive this error message if the file size is too large.
                messages.error(request, _("Uploaded file is too large."))
                return return_url

            file_data = uploaded_csv.read().decode('utf-8')

            lines = file_data.split("\n")

            skipped_codes = 0
            num_codes = 0

            for line_num, line in enumerate(lines):
                fields = line.split(",")
                num_columns = len(fields)
                # Skip any blank lines. Not an error, can just be ignored.
                if line == '':
                    continue
                if num_columns != 2:
                    # Translators: When staff upload a file containing access codes, they receive this message if a line in the file has more than 2 pieces of data.
                    messages.error(request, _("Line {line_num} has {num_columns} columns. "
                                   "Expected 2.".format(line_num=line_num+1,
                                        num_columns=num_columns)))
                    return return_url


                access_code = fields[0].strip()

                if len(access_code) > 60:
                    # Translators: When staff upload a file containing access codes, they receive this message if a code is too long for the relevant database field, likely indicating an error.
                    messages.error(request, _("Access code on line {line_num} is "
                        "too long for the database field.".format(
                            line_num=line_num+1)))
                    return return_url

                try:
                    partner_pk = int(fields[1].strip())
                except ValueError:
                    # Translators: When staff upload a file containing access codes, they receive this message if the column which should only contain a number contains anything that isn't a number.
                    messages.error(request, _("Second column should only contain "
                        "numbers. Error on line {line_num}.".format(
                            line_num=line_num+1)))
                    return return_url

                try:
                    check_partner = Partner.even_not_available.get(pk=partner_pk)
                except ObjectDoesNotExist:
                    # Translators: When staff upload a file containing access codes, they receive this message if a partner ID in the file doesn't correspond to a partner in the Library Card platform database.
                    messages.error(request, _("File contains reference to invalid "
                        "partner ID on line {line_num}".format(line_num=line_num+1)))
                    return return_url

            # Now that we've verified all access codes are valid, let's try to
            # actually upload them.
            for line in lines:
                if line == '':
                    continue
                fields = line.split(",")
                access_code = fields[0].strip()
                partner_pk = int(fields[1].strip())

                # Only upload this code if it doesn't already exist. If it does,
                # increment a counter so we can report that.
                access_code_partner_check = AccessCode.objects.filter(code=access_code,
                    partner=partner_pk).count()
                if access_code_partner_check != 0:
                    skipped_codes += 1
                else:
                    new_access_code = AccessCode()
                    new_access_code.code = access_code
                    new_access_code.partner = Partner.even_not_available.get(pk=partner_pk)
                    new_access_code.save()
                    num_codes += 1

            if num_codes > 0:
                # Translators: When staff successfully upload a file containing access codes, they receive this message.
                messages.info(request, _("{num_codes} access codes successfully "
                    "uploaded!".format(num_codes=num_codes)))
            if skipped_codes > 0:
                # Translators: When staff upload a file containing access codes, they receive this message if any were duplicates.
                messages.info(request, _("{num_duplicates} access codes ignored "
                    "as duplicates.".format(num_duplicates=skipped_codes)))
            return HttpResponseRedirect('admin')
        return render(request, 'resources/csv_form.html')

admin.site.register(AccessCode, AccessCodeAdmin)
