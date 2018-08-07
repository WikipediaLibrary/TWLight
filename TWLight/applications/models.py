# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from reversion import revisions as reversion
from reversion.models import Version

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _

from TWLight.resources.models import Partner, Stream
from TWLight.users.models import Editor


class Application(models.Model):
    class Meta:
        app_label = 'applications'
        verbose_name = 'application'
        verbose_name_plural = 'applications'
        ordering = ['-date_created', 'editor', 'partner']


    PENDING = 0
    QUESTION = 1
    APPROVED = 2
    NOT_APPROVED = 3
    SENT = 4

    STATUS_CHOICES = (
        # Translators: This is the status of an application that has not yet been reviewed.
        (PENDING, _('Pending')),
        # Translators: This is the status of an application that reviewers have asked questions about.
        (QUESTION, _('Under discussion')),
        # Translators: This is the status of an application which has been approved by a reviewer.
        (APPROVED, _('Approved')),
        # Translators: This is the status of an application which has been declined by a reviewer.
        (NOT_APPROVED, _('Not approved')),
        # Translators: This is the status of an application that has been sent to a partner.
        (SENT, _('Sent to partner')),
    )

    # This list should contain all statuses that are the end state of an
    # Application - statuses which are not expected to be further modified.
    FINAL_STATUS_LIST = [APPROVED, NOT_APPROVED, SENT]

    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    # Moved from auto_now_add=True so that we can set the date for import.
    # Defaults to today, set as non-editable, and not required in forms.
    date_created = models.DateField(default=now, editable=False)

    # Will be set on save() if status changes from PENDING/QUESTION to
    # APPROVED/NOT APPROVED.
    date_closed = models.DateField(blank=True, null=True,
        # Translators: Shown in the administrator interface for editing applications directly. Site administrators should rarely, if ever, have to change this number.
        help_text=_('Please do not override this field! Its value is set '
                  'automatically.'))

    # Will be set on save() if status changes from PENDING/QUESTION to
    # APPROVED/NOT APPROVED.
    # We can replace this field with F expressions and annotate/aggregate to get
    # all the metrics we want. This wasn't an option prior to Django 1.8 (the
    # code was originally written in 1.7), so we needed to precompute. At this
    # point the upgrade would be nice to have, but not worth the hassle of
    # updating all the things that touch this field.
    days_open = models.IntegerField(blank=True, null=True,
        help_text=_('Please do not override this field! Its value is set '
                  'automatically.'))

    sent_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL,
        # Translators: Shown in the administrator interface for editing applications directly. Labels the username of a user who flagged an application as 'sent to partner'.
        help_text=_('The user who sent this application to the partner'))

    editor = models.ForeignKey(Editor, related_name='applications', null=True,
        on_delete=models.SET_NULL)
    partner = models.ForeignKey(Partner, related_name='applications')

    rationale = models.TextField(blank=True)
    specific_title = models.CharField(max_length=128, blank=True)
    specific_stream = models.ForeignKey(Stream,
                            related_name='applications',
                            blank=True, null=True)
    comments = models.TextField(blank=True)
    agreement_with_terms_of_use = models.BooleanField(default=False)
    account_email = models.CharField(max_length=64, blank=True, null=True)

    # Was this application imported via CLI?
    imported = models.NullBooleanField(default=False)

    # If this Application is a renewal, the parent is the original Application
    # it was copied from.
    parent = models.ForeignKey('self',
        on_delete=models.SET_NULL, blank=True, null=True)

    hidden = models.BooleanField(default=False)

    def __unicode__(self):
        return u'{self.editor} - {self.partner}'.format(self=self)


    def get_absolute_url(self):
        return reverse_lazy('applications:evaluate', kwargs={'pk': self.pk})

    # Every single save to this model should create a revision.
    # You can access two models this way: REVISIONS and VERSIONS.
    # Versions contain the model data at the time, accessible via
    # version.field_dict['field_name']. Revisions contain metadata about the
    # version (like when it was saved).
    # See http://django-reversion.readthedocs.io/en/release-1.8/.
    # See TWLight/applications/templatetags/version_tags for how to display
    # version-related information in templates; the API is not always
    # straightforward so we wrap it there.
    @reversion.create_revision()
    def save(self, *args, **kwargs):
        super(Application, self).save(*args, **kwargs)


    def renew(self):
        """
        Create a reviewable clone of this application: that is, a PENDING
        application dated today with the same user-submitted data (but with
        data related to application review blanked out). Return the clone if
        successful and None otherwise.
        """
        if not self.is_renewable:
            return None
        else:
            data = model_to_dict(self,
                    fields=['rationale', 'specific_title', 'comments',
                            'agreement_with_terms_of_use', 'account_email'])

            # Status and parent are explicitly different on the child than
            # on the parent application. For editor, partner, and stream, we
            # need to pull those directly - model_to_dict will give us the pks
            # of the referenced objects, but we need the actual objects.
            data.update({'status': self.PENDING, 
                         'parent': self,
                         'editor': self.editor,
                         'partner': self.partner,
                         'specific_stream': self.specific_stream,
                         'account_email': self.account_email})

            # Create clone. We can't use the normal approach of setting the
            # object's pk to None and then saving it, because the object in
            # this case is 'self', and weird things happen.
            clone = Application(**data)
            clone.save()

            return clone


    LABELMAKER = {
        PENDING: '-primary',
        QUESTION: '-warning',
        APPROVED: '-success',
        NOT_APPROVED: '-danger',
        SENT: '-success',
    }

    def get_bootstrap_class(self):
        """
        What class should be applied to Bootstrap labels, buttons, alerts, etc.
        for this application?

        Returns a string like '-default'; the template is responsible for
        prepending 'label' or 'button', etc., as appropriate to the HTML object.
        """
        try:
            return self.LABELMAKER[self.status]
        except KeyError:
            return None


    def get_version_count(self):
        try:
            return len(Version.objects.get_for_object(self))
        except TypeError:
            # When we call this the *first* time we save an object, it will fail
            # as the object properties that reversion is looking for are not
            # yet set.
            return None


    def get_latest_version(self):
        try:
            return Version.objects.get_for_object(self)[0]
        except (TypeError, IndexError):
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
            try:
                return revision.user.editor.wp_username
            except AttributeError:
                return None
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
            assert self.status in [self.APPROVED, self.NOT_APPROVED, self.SENT]
            return (self.date_closed - self.date_created).days


    @property
    def user(self):
        # Needed by CoordinatorOrSelf mixin, e.g. on the application evaluation
        # view.
        return self.editor.user


    @property
    def is_renewable(self):
        """
        Apps are eligible for renewal if they are approved and have not already
        been renewed. (We presume that SENT apps were at some point APPROVED.)
        """
        return all([not bool(Application.objects.filter(parent=self)),
                    self.status in [self.APPROVED, self.SENT],
                    self.partner.renewals_available])


# IMPORTANT: pre_save is not sent by Queryset.update(), so *none of this
# behavior will happen on if you update() an Application queryset*.
# That is sometimes okay (for instance, if you are turning an APPROVED app into
# a SENT app, since days_open and date_closed were set on approval), but it is
# not always okay. Errors caused by days_open not existing when expected to
# exist can show up in weird parts of the application (for example, template
# rendering failing when get_num_days_open returns None but its output is
# passed to a template filter that needs an integer).
@receiver(pre_save, sender=Application)
def update_app_status_on_save(sender, instance, **kwargs):

    # Make sure not using a mix of dates and dateimes
    if instance.date_created and isinstance(instance.date_created, datetime):
        instance.date_created = instance.date_created.date()

    # Make sure not using a mix of dates and dateimes
    if instance.date_closed and isinstance(instance.date_closed, datetime):
        instance.date_closed = instance.date_closed.date()

    if instance.id:
        orig_app = Application.objects.get(pk=instance.id)
        orig_status = orig_app.status
        if all([orig_status not in Application.FINAL_STATUS_LIST,
                int(instance.status) in Application.FINAL_STATUS_LIST,
                not bool(instance.date_closed)]):

            instance.date_closed = localtime(now()).date()
            instance.days_open = \
                (instance.date_closed - instance.date_created).days

    else:
        # If somehow we've created an Application whose status is final
        # at the moment of creation, set its date-closed-type parameters
        # too.
        if (instance.status in Application.FINAL_STATUS_LIST
            and not instance.date_closed):

            instance.date_closed = localtime(now()).date()
            instance.days_open = 0
