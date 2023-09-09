from django.contrib import admin

from .models import CommunityPage

class ConfigAdmin(admin.ModelAdmin):
    model = CommunityPage

    list_display = (
        'lang',
        'url',
    )

admin.site.register(CommunityPage, ConfigAdmin)
