# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management.base import NoArgsCommand

from ... import core


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        core._send_pending_messages()
        core._mark_discarded_messages()
        core._retry_send_messages()

        return 0
