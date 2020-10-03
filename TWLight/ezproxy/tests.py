# -*- coding: utf-8 -*-

from datetime import date, timedelta
import urllib.parse
from urllib.parse import quote

from django.conf import settings
from django.urls import reverse
from TWLight.tests import AuthorizationBaseTestCase
from TWLight.resources.tests import EditorCraftRoom
from TWLight.users.models import Authorization


class ProxyTestCase(AuthorizationBaseTestCase):
    """
    Tests for Proxy Authorizations.
    """

    def test_authorization_url(self):
        """
        Check to see if the URL-based endpoint correctly sends users on to EZProxy.
        We're testing it rather the token-based endpoint because we can check the target URL.
        """
        self.editor1 = EditorCraftRoom(
            self, Terms=True, Coordinator=False, editor=self.editor1
        )
        response = self.client.get(
            reverse(
                "ezproxy:ezproxy_auth_u", kwargs={"url": self.app1.partner.target_url}
            )
        )
        # verify that we get a redirect to the proxy server
        # We're validating everything but the ticket contents
        # because the ticket is deterministic based on the input ... and it would be a pain to write a test for it.
        self.assertEqual(response.status_code, 302)
        too_lazy_to_test_ticket = quote(
            urllib.parse.parse_qs(response.url)["ticket"][0]
        )
        expected_url = (
            settings.TWLIGHT_EZPROXY_URL
            + "/login?user="
            + quote(self.editor1.wp_username)
            + "&ticket="
            + too_lazy_to_test_ticket
            + "&auth="
            + settings.TWLIGHT_ENV
            + "&url="
            + self.app1.partner.target_url
        )
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

        # Users without valid authorization can't get in.
        # Let's be mean and delete all of this user's authorizations.
        for user_authorization in Authorization.objects.filter(user=self.editor1.user):
            user_authorization.date_expires = date.today() - timedelta(days=1)
            user_authorization.save()

        response = self.client.get(
            reverse(
                "ezproxy:ezproxy_auth_u", kwargs={"url": self.app1.partner.target_url}
            )
        )

        # verify that was denied.
        self.assertEqual(response.status_code, 403)
