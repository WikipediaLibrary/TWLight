from subprocess import check_output
from django.conf import settings
from django.core import management
from django_cron import CronJobBase, Schedule

WEEKLY = 10080
DAILY = 1440


class SendCoordinatorRemindersCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=WEEKLY)
    code = "applications.send_coordinator_reminders"

    def do(self):
        management.call_command("send_coordinator_reminders")


class BackupCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "backup"

    def do(self):
        # Using check_output here because we want to log STDOUT.
        # To avoid logging for commands with sensitive output, import and use
        # subprocess.call instead of subprocess.check_output.
        return check_output([settings.TWLIGHT_HOME + "/bin/twlight_backup.sh"])


class UserRenewalNoticeCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "users.user_renewal_notices"

    def do(self):
        management.call_command("user_renewal_notice")


class ProxyWaitlistDisableCronJob(CronJobBase):
    schedule = Schedule(run_every_mins=DAILY)
    code = "resources.proxy_waitlist_disable"

    def do(self):
        management.call_command("proxy_waitlist_disable")
