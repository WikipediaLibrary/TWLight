import reversion

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.utils.translation import ugettext as _

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


    def get_latest_version(self):
        return reversion.get_for_object(self)[0]


    def get_latest_revision(self):
        return self.get_latest_version().revision


    # TODO: order_by
