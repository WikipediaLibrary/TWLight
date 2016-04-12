from reversion.admin import VersionAdmin

from django.contrib import admin

from .models import Application


class ApplicationAdmin(VersionAdmin):
    search_fields = ('partner__company_name', 'user__username')
    list_display = ('id', 'partner', 'user',)
    raw_id_fields = ('user',)

    # reversion options
    history_latest_first = True

admin.site.register(Application, ApplicationAdmin)
