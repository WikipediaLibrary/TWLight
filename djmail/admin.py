# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib import admin

from . import models


class MessageAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'from_email', 'to_email', 'status', 'priority', 'created_at', 'sent_at', 'retry_count']
    list_filter = ['status', 'priority', 'created_at', 'sent_at', 'retry_count']
    search_fields = ['from_email', 'to_email', 'subject', 'uuid']

admin.site.register(models.Message, MessageAdmin)
