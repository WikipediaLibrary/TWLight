from django.contrib import admin

from .models import Application


class ApplicationAdmin(admin.ModelAdmin):
    search_fields = ('partner__company_name', 'user__username')
    list_display = ('id', 'partner', 'user',)
    raw_id_fields = ('user',)

admin.site.register(Application, ApplicationAdmin)
