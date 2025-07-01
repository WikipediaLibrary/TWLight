from subprocess import check_output
from django.conf import settings
from django.core import management
from django_cron import CronJobBase, Schedule
from sentry_sdk import capture_exception

WEEKLY = 10080
DAILY = 1440
SEMI_DAILY = 720


class SendCoordinatorRemindersCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=WEEKLY)
    code = "applications.send_coordinator_reminders"

    def do(self):
        try:
            management.call_command("send_coordinator_reminders")
        except Exception as e:
            capture_exception(e)


class BackupCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=SEMI_DAILY)
    code = "backup"

    def do(self):
        try:
            # Using check_output here because we want to log STDOUT.
            # To avoid logging for commands with sensitive output, import and use
            # subprocess.call instead of subprocess.check_output.
            return check_output(
                [settings.TWLIGHT_HOME + "/bin/twlight_backup.sh"], text=True
            )
        except Exception as e:
            capture_exception(e)


class UserRenewalNoticeCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "users.user_renewal_notices"

    def do(self):
        try:
            management.call_command("user_renewal_notice")
        except Exception as e:
            capture_exception(e)


class ProxyWaitlistDisableCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "resources.proxy_waitlist_disable"

    def do(self):
        try:
            management.call_command("proxy_waitlist_disable")
        except Exception as e:
            capture_exception(e)


class UserUpdateEligibilityCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "users.user_update_eligibility"

    def do(self):
        try:
            management.call_command("user_update_eligibility")
        except Exception as e:
            capture_exception(e)


class ClearSessions(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "django.contrib.sessions.clearsessions"

    def do(self):
        try:
            management.call_command("clearsessions")
        except Exception as e:
            capture_exception(e)


class DeleteOldEmails(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "djmail.djmail_delete_old_messages"

    def do(self):
        try:
            management.call_command("djmail_delete_old_messages", days=100)
        except Exception as e:
            capture_exception(e)


class RetrieveMonthlyUsers(CronJobBase):
    schedule = Schedule(run_monthly_on_days=1)
    code = "users.retrieve_monthly_users"

    def do(self):
        try:
            management.call_command("retrieve_monthly_users")
        except Exception as e:
            capture_exception(e)
