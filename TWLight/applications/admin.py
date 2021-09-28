from reversion.admin import VersionAdmin

from django.contrib import admin

from .models import Application


class ApplicationAdmin(VersionAdmin):
    search_fields = ("partner__company_name", "editor__wp_username")
    list_display = ("id", "partner", "editor")
    list_filter = ("status", "partner")
    raw_id_fields = ("editor", "sent_by", "parent", "partner")

    # reversion options
    history_latest_first = True


admin.site.register(Application, ApplicationAdmin)
