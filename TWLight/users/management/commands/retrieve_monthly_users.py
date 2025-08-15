import calendar
import datetime
from dateutil.relativedelta import relativedelta
import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger("django")


class Command(BaseCommand):
    help = "Retrieves user names that have logged-in in the past month and have approved applications and current authorizations."

    def info(self, msg):
        # Log and print so that messages are visible
        # in docker logs (log) and cron job logs (print)
        logger.info(msg)
        self.stdout.write(msg)
        self.stdout.flush()

    def handle(self, *args, **options):
        current_date = datetime.datetime.now(datetime.timezone.utc).date()
        last_month = current_date - relativedelta(months=1)
        first_day_last_month = datetime.date(last_month.year, last_month.month, 1)
        _, last_day = calendar.monthrange(last_month.year, last_month.month)
        last_day_last_month = datetime.date(last_month.year, last_month.month, last_day)

        self.info("Getting query...")
        raw_query = """SELECT users_editor.wp_username, IF(
            -- has application status APPROVED = 2 SENT = 4
            (applications_application.status = 2 OR applications_application.status = 4), 'true', 'false') AS has_approved_apps,
            -- has authorizations that were:
            IF((
              -- created no more than a year ago or
              users_authorization.date_authorized >= date_sub(now(),interval 1 year) OR
              -- expired no more than a year ago or
              users_authorization.date_expires >= date_sub(now(),interval 1 year) OR
              -- are currently active (eg. have currently associated partners)
              COUNT(users_authorization_partners.id) > 0
            ), 'true', 'false') AS has_current_auths
        FROM auth_user JOIN users_editor ON auth_user.id = users_editor.user_id
        -- left outer join used to grab apps for approved_apps virtual column
        LEFT OUTER JOIN applications_application ON users_editor.id = applications_application.editor_id
        -- left outer join used to grab auths for current_auths virtual column
        LEFT OUTER JOIN users_authorization ON auth_user.id = users_authorization.user_id
        -- left outer join used to grab auth partners for current_auths virtual column
        LEFT OUTER JOIN users_authorization_partners ON users_authorization.id = users_authorization_partners.authorization_id
        -- limit to people who logged in within the last month
        WHERE auth_user.last_login >= '{first_day_last_month}' AND auth_user.last_login <= '{last_day_last_month}'
        GROUP BY users_editor.wp_username;""".format(
            first_day_last_month=first_day_last_month,
            last_day_last_month=last_day_last_month,
        )

        self.info("Creating monthly users...")
        with connection.cursor() as cursor:
            cursor.execute(raw_query)
            columns = [col[0] for col in cursor.description]
            monthly_users = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if monthly_users:
            self.info("Sending email...")
            call_command(
                "send_email_via_api",
                target="Suecarmol",  # TODO: change to Vipin's user
                subject="Monthly user report",
                body=f"Here is a list of monthly users: {monthly_users}",
            )
