from subprocess import check_output
from django.conf import settings
from django.core import management
from django_cron import CronJobBase, Schedule
from sentry_sdk import capture_exception

WEEKLY = 10080
DAILY = 1440


class SendCoordinatorRemindersCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=WEEKLY)
    code = "applications.send_coordinator_reminders"

    def do(self):
        try:
            management.call_command("send_coordinator_reminders")
        except Exception as e:
            capture_exception(e)


class BackupCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "backup"

    def do(self):
        try:
            # Using check_output here because we want to log STDOUT.
            # To avoid logging for commands with sensitive output, import and use
            # subprocess.call instead of subprocess.check_output.
            return check_output([settings.TWLIGHT_HOME + "/bin/twlight_backup.sh"])
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
