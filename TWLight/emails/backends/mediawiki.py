"""
Email backend that POSTs messages to the MediaWiki Emailuser endpoint.
see: https://www.mediawiki.org/wiki/API:Emailuser
"""
import logging
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
                        "ConnectionError, retrying in {}s".format(self.retry_after_conn)
                    )
                    sleep(retry_after_conn)
                    continue

        return conn

    return wrapper


def _json_maxlag(response):
    """A helper method that handles maxlag retries."""
    data = response.json()
    try:
        if data["error"]["code"] != "maxlag":
            return data
    except KeyError:
        return data

    retry_after = float(response.headers.get("Retry-After", 5))
    retry_on_lag_error = 50
    no_retry = 0 <= retry_on_lag_error < try_count

    message = "Server exceeded maxlag"
    if not no_retry:
        message += ", retrying in {}s".format(retry_after)
    if "lag" in data["error"]:
        message += ", lag={}".format(data["error"]["lag"])
    message += ", API=".format(self.url)

    log = logger.warning if no_retry else logger.info
    log(
        message,
        {
            "code": "maxlag-retry",
            "retry-after": retry_after,
            "lag": data["error"]["lag"] if "lag" in data["error"] else None,
            "x-database-lag": response.headers.get("X-Database-Lag", 5),
        },
    )

    if no_retry:
        raise Exception(message)

    sleep(retry_after)


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
            # GET request to fetch login token
            login_token_params = {
                "action": "query",
                "meta": "tokens",
                "type": "login",
                "maxlag": self.maxlag,
                "format": "json",
            }
            session = Session()
            logger.info("Session created, getting login token...")
            response_login_token = session.get(url=self.url, params=login_token_params)
            if response_login_token.status_code != 200:
                raise Exception(
                    "There was an error in the request for obtaining the login token."
                )
            login_token_data = _json_maxlag(response_login_token)
            login_token = login_token_data["query"]["tokens"]["logintoken"]
            if not login_token:
                raise Exception("There was an error obtaining the login token.")

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
            login_response = session.post(url=self.url, data=login_params)
            if login_response.status_code != 200:
                raise Exception("There was an error in the request for the login.")

            # GET request to fetch Email token
            # see: https://www.mediawiki.org/wiki/API:Emailuser#Token
            email_token_params = {"action": "query", "meta": "tokens", "format": "json"}

            logger.info("Getting email token...")
            email_token_response = session.get(url=self.url, params=email_token_params)
            if email_token_response.status_code != 200:
                raise Exception(
                    "There was an error in the request for the email token."
                )

            email_token_data = _json_maxlag(email_token_response)

            email_token = email_token_data["query"]["tokens"]["csrftoken"]
            if not email_token:
                raise Exception("There was an error obtaining the email token.")

            # Assign the session and email token
            self.email_token = email_token
            self.session = session
            logger.info("Email API session ready.")
            return True
        except:
            if not self.fail_silently:
                raise

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
                target_qs = Editor.objects.values_list("wp_username", flat=True).filter(
                    user__email=recipient
                )
                target_qs_count = target_qs.count()
                if target_qs_count > 1:
                    raise Exception(
                        "Email address associated with {} user accounts, email skipped".format(
                            target_qs_count
                        )
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

                logger.info("Checking if user is emailable...")
                emailable_response = self.session.post(
                    url=self.url, data=emailable_params
                )
                if emailable_response.status_code != 200:
                    raise Exception(
                        "There was an error in the request to check if the user can receive emails."
                    )
                emailable_data = _json_maxlag(emailable_response)
                emailable = "emailable" in emailable_data["query"]["users"][0]
                if not emailable:
                    raise Exception("User not emailable, email skipped.")

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
                emailuser_response = self.session.post(url=self.url, data=email_params)
                if emailuser_response.status_code != 200:
                    raise Exception(
                        "There was an error in the request to send the email."
                    )
                emailuser_data = _json_maxlag(emailuser_response)
                if emailuser_data["emailuser"]["result"] != "Success":
                    raise Exception("There was an error when trying to send the email.")
                logger.info("Email sent.")
        except:
            if not self.fail_silently:
                raise
            return False
        return True
