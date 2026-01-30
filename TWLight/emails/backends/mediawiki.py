"""
Email backend that POSTs messages to the MediaWiki Emailuser endpoint.
see: https://www.mediawiki.org/wiki/API:Emailuser
"""

import logging
from json import dumps
from requests import Session
from requests.exceptions import ConnectionError
from requests.structures import CaseInsensitiveDict
from time import sleep

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from TWLight.users.models import Editor

logger = logging.getLogger(__name__)


def retry_conn():
    """A decorator that handles connection retries."""
    retry_delay = 0
    retry_on_connection_error = 10
    retry_after_conn = 5

    def wrapper(func):
        def conn(*args, **kwargs):
            try_count = 0
            try_count_conn = 0
            while True:
                try_count += 1
                try_count_conn += 1

                if retry_delay:
                    sleep(retry_delay)
                try:
                    return func(*args, **kwargs)
                except ConnectionError as e:
                    no_retry_conn = 0 <= retry_on_connection_error < try_count_conn
                    if no_retry_conn:
                        logger.warning("ConnectionError exhausted retries")
                        raise e
                    logger.warning(
                        "ConnectionError, retrying in {}s".format(retry_after_conn)
                    )
                    sleep(retry_after_conn)
                    continue

        return conn

    return wrapper


class EmailBackend(BaseEmailBackend):
    def __init__(
        self,
        url=None,
        timeout=None,
        delay=None,
        retry_delay=None,
        maxlag=None,
        username=None,
        password=None,
        fail_silently=False,
        **kwargs,
    ):
        super().__init__(fail_silently=fail_silently)
        self.url = settings.MW_API_URL if url is None else url
        self.headers = CaseInsensitiveDict()
        self.headers["User-Agent"] = "{}/0.0.1".format(__name__)
        self.url = settings.MW_API_URL if url is None else url
        self.timeout = settings.MW_API_REQUEST_TIMEOUT if timeout is None else timeout
        self.delay = settings.MW_API_REQUEST_DELAY if delay is None else delay
        self.retry_delay = (
            settings.MW_API_REQUEST_RETRY_DELAY if retry_delay is None else retry_delay
        )
        self.maxlag = settings.MW_API_MAXLAG if maxlag is None else maxlag
        self.username = settings.MW_API_EMAIL_USER if username is None else username
        self.password = settings.MW_API_EMAIL_PASSWORD if password is None else password
        self.email_token = None
        self.session = None
        logger.info("Email connection constructed.")

    def _handle_request(self, response, try_count=0):
        """
        A helper method that handles MW API responses
        including maxlag retries.
        """
        # Raise for any HTTP response errors
        if response.status_code != 200:
            raise Exception("HTTP {} error".format(response.status_code))
        data = response.json()
        error = data.get("error", {})
        if "warnings" in data:
            logger.warning(dumps(data["warnings"], indent=True))
        # raise for any api error codes besides max lag
        try:
            if error.get("code") != "maxlag":
                raise Exception(dumps(error))
        except:
            # return data if there are no errors
            return data

        # handle retries with max lag
        lag = error.get("lag")
        request = response.request
        retry_after = float(response.headers.get("Retry-After", 5))
        retry_on_lag_error = 50
        no_retry = 0 <= retry_on_lag_error < try_count
        message = "Server exceeded maxlag"
        if not no_retry:
            message += ", retrying in {}s".format(retry_after)
        if lag:
            message += ", lag={}".format(lag)
        message += ", url={}".format(self.url)
        log = logger.warning if no_retry else logger.info
        log(
            message,
            {
                "code": "maxlag-retry",
                "retry-after": retry_after,
                "lag": lag,
                "x-database-lag": response.headers.get("X-Database-Lag", 5),
            },
        )
        if no_retry:
            raise Exception(message)

        sleep(retry_after)
        try_count += 1
        return self._handle_request(self.session.send(request), try_count)

    @retry_conn()
    def open(self):
        """
        Ensure an open session to the API server. Return whether or not a
        new session was required (True or False) or None if an exception
        passed silently.
        """
        if self.session:
            # Nothing to do if the session exists
            return False

        try:
            self.session = Session()
            self.session.headers = self.headers
            logger.info("Session created, getting login token...")

            # GET request to fetch login token
            login_token_params = {
                "action": "query",
                "meta": "tokens",
                "type": "login",
                "maxlag": self.maxlag,
                "format": "json",
            }
            login_token_response = self._handle_request(
                self.session.get(url=self.url, params=login_token_params)
            )
            login_token = login_token_response["query"]["tokens"]["logintoken"]
            if not login_token:
                self.session = None
                raise Exception(dumps(login_token_response))

            # POST request to log in. Use of main account for login is not
            # supported. Obtain credentials via Special:BotPasswords
            # (https://www.mediawiki.org/wiki/Special:BotPasswords) for lgname & lgpassword
            login_params = {
                "action": "login",
                "lgname": self.username,
                "lgpassword": self.password,
                "lgtoken": login_token,
                "maxlag": self.maxlag,
                "format": "json",
            }
            logger.info("Signing in...")
            login_response = self._handle_request(
                self.session.post(url=self.url, data=login_params)
            )

            # GET request to fetch Email token
            # see: https://www.mediawiki.org/wiki/API:Emailuser#Token
            email_token_params = {"action": "query", "meta": "tokens", "format": "json"}

            logger.info("Getting email token...")
            email_token_response = self._handle_request(
                self.session.get(url=self.url, params=email_token_params)
            )
            email_token = email_token_response["query"]["tokens"]["csrftoken"]
            if not email_token:
                self.session = None
                raise Exception(dumps(email_token_response))

            # Assign the email token
            self.email_token = email_token
            logger.info("Email API session ready.")
            return True
        except Exception as e:
            if not self.fail_silently:
                raise e

    def close(self):
        """Unset the session."""
        self.email_token = None
        self.session = None
        logger.info("Session destroyed.")

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0
        new_session_created = self.open()
        if not self.session or new_session_created is None:
            # We failed silently on open().
            # Trying to send would be pointless.
            return 0
        num_sent = 0
        for message in email_messages:
            sent = self._send(message)
            if sent:
                num_sent += 1
        if new_session_created:
            self.close()
        return num_sent

    @retry_conn()
    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False

        try:
            for recipient in email_message.recipients():
                # lookup the target editor from the email address
                target_qs = Editor.objects.filter(user__email=recipient).values_list(
                    "wp_username", flat=True
                )
                target_qs_count = target_qs.count()
                if target_qs_count > 1:
                    raise Exception(
                        "skip shared email address: {}".format(list(target_qs))
                    )

                target = target_qs.first()

                # GET request to check if user is emailable
                emailable_params = {
                    "action": "query",
                    "list": "users",
                    "ususers": target,
                    "usprop": "emailable",
                    "maxlag": self.maxlag,
                    "format": "json",
                }

                emailable_response = self._handle_request(
                    self.session.post(url=self.url, data=emailable_params)
                )
                emailable = "emailable" in emailable_response["query"]["users"][0]
                if not emailable:
                    raise Exception("skip not emailable: {}".format(target))

                # POST request to send an email
                email_params = {
                    "action": "emailuser",
                    "target": target,
                    "subject": email_message.subject,
                    "text": email_message.body,
                    "token": self.email_token,
                    "maxlag": self.maxlag,
                    "format": "json",
                }

                logger.info("Sending email...")
                emailuser_response = self._handle_request(
                    self.session.post(url=self.url, data=email_params)
                )
                result = emailuser_response.get("emailuser", {}).get("result")
                if result != "Success":
                    raise Exception(dumps(emailuser_response))

                logger.info("Email sent.")
        except Exception as e:
            if not self.fail_silently:
                raise e
            return False
        return True
