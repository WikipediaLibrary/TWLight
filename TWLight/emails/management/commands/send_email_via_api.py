import logging
import os
import requests

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger("django")


class Command(BaseCommand):
    help = "Command that sends emails via API:Emailuser in MediaWiki"

    def info(self, msg):
        # Log and print so that messages are visible
        # in docker logs (log) and cron job logs (print)
        logger.info(msg)
        self.stdout.write(msg)
        self.stdout.flush()

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            "--target",
            type=str,
            help="The Wikipedia username you want to send the email to.",
        )
        parser.add_argument(
            "--subject",
            type=str,
            help="The subject of the email.",
        )
        parser.add_argument(
            "--body",
            type=str,
            help="The body of the email.",
        )

    def handle(self, *args, **options):
        if not options["target"]:
            raise CommandError("You need to specify a user to send the email to")

        if not options["subject"]:
            raise CommandError("You need to specify the subject of the email")

        if not options["body"]:
            raise CommandError("You need to specify the body of the email")

        target = options["target"]
        subject = options["subject"]
        body = options["body"]

        email_bot_username = os.environ.get("EMAILWIKIBOTUSERNAME", None)
        email_bot_password = os.environ.get("EMAILWIKIBOTPASSWORD", None)

        if email_bot_username is None or email_bot_password is None:
            # Bot credentials not provided; exiting gracefully
            raise CommandError(
                "The email bot username and/or password were not provided. Exiting..."
            )
        # Code taken in part from https://www.mediawiki.org/wiki/API:Emailuser#Python
        session = requests.Session()
        # TODO: See if we need to change this to Meta or the user's home wiki?
        # Or is this wiki fine?
        url = "https://test.wikipedia.org/w/api.php"

        # Step 1: GET request to fetch login token
        login_token_params = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        }

        self.info("Getting login token...")
        response_login_token = session.get(url=url, params=login_token_params)
        if response_login_token.status_code != 200:
            raise CommandError(
                "There was an error in the request for obtaining the login token."
            )
        login_token_data = response_login_token.json()

        login_token = login_token_data["query"]["tokens"]["logintoken"]

        if not login_token:
            raise CommandError("There was an error obtaining the login token.")

        # Step 2: POST request to log in. Use of main account for login is not
        # supported. Obtain credentials via Special:BotPasswords
        # (https://www.mediawiki.org/wiki/Special:BotPasswords) for lgname & lgpassword
        login_params = {
            "action": "login",
            "lgname": email_bot_username,
            "lgpassword": email_bot_password,
            "lgtoken": login_token,
            "format": "json",
        }

        self.info("Signing in...")
        login_response = session.post(url, data=login_params)
        if login_response.status_code != 200:
            raise CommandError("There was an error in the request for the login.")

        # Step 3: GET request to fetch Email token
        email_token_params = {"action": "query", "meta": "tokens", "format": "json"}

        self.info("Getting emwail token...")
        email_token_response = session.get(url=url, params=email_token_params)
        email_token_data = email_token_response.json()

        email_token = email_token_data["query"]["tokens"]["csrftoken"]

        # Step 4: POST request to send an email
        email_params = {
            "action": "emailuser",
            "target": target,
            "subject": subject,
            "text": body,
            "token": email_token,
            "format": "json",
        }

        self.info("Sending email...")
        email_response = session.post(url, data=email_params)
        if email_response.status_code != 200:
            raise CommandError("There was an error when trying to send the email.")
