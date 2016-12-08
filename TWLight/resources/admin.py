from django.contrib import admin

from .models import Partner, Stream, Contact, Language


class LanguageAdmin(admin.ModelAdmin):
    search_fields = ('language',)
    list_display = ('language',)

admin.site.register(Language, LanguageAdmin)


class PartnerAdmin(admin.ModelAdmin):
    search_fields = ('company_name',)
    list_display = ('company_name', 'description', 'id', 'get_languages')

admin.site.register(Partner, PartnerAdmin)



class StreamAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'name',)
    list_display = ('id', 'partner', 'name', 'description', 'get_languages')

admin.site.register(Stream, StreamAdmin)



class ContactAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'full_name', 'short_name',)
    list_display = ('id', 'title', 'full_name', 'partner', 'email',)

admin.site.register(Contact, ContactAdmin)
