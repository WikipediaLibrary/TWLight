from datetime import date
import reversion

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.utils.translation import ugettext_lazy as _

from TWLight.resources.models import Partner, Stream


class Application(models.Model):
    class Meta:
        app_label = 'applications'


    PENDING = 0
    QUESTION = 1
    APPROVED = 2
    NOT_APPROVED = 3

    STATUS_CHOICES = (
        (PENDING, _('Pending')),
        (QUESTION, _('Under discussion')),
        (APPROVED, _('Approved')),
        (NOT_APPROVED, _('Not approved')),
    )

    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    date_created = models.DateField(auto_now_add=True)

    # Will be set on save() if status changes from PENDING/QUESTION to
    # APPROVED/NOT APPROVED.
    date_closed = models.DateField(blank=True, null=True,
        help_text=_('Do not override this field! Its value is set automatically '
                  'when the application is saved, and overriding it may have '
                  'undesirable results.'))

    user = models.ForeignKey(User, related_name='applications')
    partner = models.ForeignKey(Partner, related_name='applications')

    rationale = models.TextField(blank=True)
    specific_title = models.CharField(max_length=128, blank=True)
    specific_stream = models.ForeignKey(Stream,
                            related_name='applications',
                            blank=True, null=True)
    comments = models.TextField(blank=True)
    agreement_with_terms_of_use = models.BooleanField(default=False)


    def __str__(self):
        return '{self.user} - {self.partner}'.format(self=self)


    def get_absolute_url(self):
        return reverse_lazy('applications:evaluate', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        version = self.get_latest_version()
        if version:
            orig_status = version.field_dict['status']
            if (orig_status in [self.PENDING, self.QUESTION]
                and self.status in [self.APPROVED, self.NOT_APPROVED]
                and not self.date_closed):

                self.date_closed = date.today()

        super(Application, self).save(*args, **kwargs)



    LABELMAKER = {
        PENDING: '-primary',
        QUESTION: '-warning',
        APPROVED: '-success',
        NOT_APPROVED: '-danger',
    }

    def get_bootstrap_class(self):
        """
        What class should be applied to Bootstrap labels, buttons, alerts, etc.
        for this application?

        Returns a string like '-default'; the template is responsible for
        prepending 'label' or 'button', etc., as appropriate to the HTML object.
        """
        return self.LABELMAKER[self.status]


    def get_version_count(self):
        return len(reversion.get_for_object(self))


    def get_latest_version(self):
        try:
            return reversion.get_for_object(self)[0]
        except TypeError:
            # If no versions yet...
            return None


    def get_latest_revision(self):
        version = self.get_latest_version()

        if version:
            return version.revision
        else:
            return None


    def get_latest_reviewer(self):
        revision = self.get_latest_revision()

        if revision:
            return revision.user
        else:
            return None


    def get_latest_review_date(self):
        revision = self.get_latest_revision()

        if revision:
            return revision.date_created
        else:
            return None


    def get_num_days_open(self):
        """
        If the application has status PENDING or QUESTION, return the # of days
        since the application was initiated. Otherwise, get the # of days
        elapsed from application initiation to final status determination.
        """
        if self.status in [self.PENDING, self.QUESTION]:
            return (date.today() - self.date_created).days
        else:
            assert self.status in [self.APPROVED, self.NOT_APPROVED]
            return (self.date_closed - self.date_created).days

    # TODO: order_by
