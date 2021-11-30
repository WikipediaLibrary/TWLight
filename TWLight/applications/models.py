# -*- coding: utf-8 -*-
import logging

from datetime import date
from reversion import revisions as reversion
from reversion.models import Version

from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.db import models
from django.forms.models import model_to_dict
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from TWLight.resources.models import Partner
from TWLight.users.models import Editor, Authorization

logger = logging.getLogger(__name__)


class ValidApplicationsManager(models.Manager):
    """
    This custom model manager excludes applications marked 'invalid' from querysets by default.
    """

    def get_queryset(self):
        return (
            super(ValidApplicationsManager, self)
            .get_queryset()
            .exclude(status=Application.INVALID)
        )


class Application(models.Model):
    class Meta:
        app_label = "applications"
        verbose_name = "application"
        verbose_name_plural = "applications"
        ordering = ["-date_created", "editor", "partner"]

    # Managers defined here
    include_invalid = models.Manager()
    objects = ValidApplicationsManager()

    PENDING = 0
    QUESTION = 1
    APPROVED = 2
    NOT_APPROVED = 3
    SENT = 4
    INVALID = 5

    STATUS_CHOICES = [
        # Translators: This is the status of an application that has not yet been reviewed.
        (PENDING, _("Pending")),
        # Translators: This is the status of an application that reviewers have asked questions about.
        (QUESTION, _("Under discussion")),
        # Translators: This is the status of an application which has been approved by a reviewer.
        (APPROVED, _("Approved")),
        # Translators: This is the status of an application which has been declined by a reviewer.
        (NOT_APPROVED, _("Not approved")),
        # Translators: This is the status of an application that has been sent to a partner upon approval.
        (SENT, _("Sent to partner")),
        # Translators: This is the status of an application that has been marked as invalid, therefore not as such declined.
        (INVALID, _("Invalid")),
    ]

    # This list should contain all statuses that are the end state of an
    # Application - statuses which are not expected to be further modified.
    FINAL_STATUS_LIST = [APPROVED, NOT_APPROVED, SENT, INVALID]

    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)

    # Defaults to today, set as non-editable, and not required in forms.
    date_created = models.DateField(default=now, editable=False)

    # Will be set on save() if status changes from PENDING/QUESTION to
    # APPROVED/NOT APPROVED, as defined via post_save signals.
    date_closed = models.DateField(
        blank=True,
        null=True,
        help_text="Please do not override this field! Its value is set automatically.",
    )

    # Will be set on save() if status changes from PENDING/QUESTION to
    # APPROVED/NOT APPROVED.
    # We can replace this field with F expressions and annotate/aggregate to get
    # all the metrics we want. This wasn't an option prior to Django 1.8 (the
    # code was originally written in 1.7), so we needed to precompute. At this
    # point the upgrade would be nice to have, but not worth the hassle of
    # updating all the things that touch this field.
    days_open = models.IntegerField(
        blank=True,
        null=True,
        help_text="Please do not override this field! Its value is set automatically.",
    )

    sent_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The user who sent this application to the partner",
    )

    editor = models.ForeignKey(
        Editor, related_name="applications", null=True, on_delete=models.SET_NULL
    )
    partner = models.ForeignKey(
        Partner, related_name="applications", on_delete=models.CASCADE
    )

    rationale = models.TextField(blank=True)
    specific_title = models.CharField(max_length=128, blank=True)
    comments = models.TextField(blank=True)
    agreement_with_terms_of_use = models.BooleanField(default=False)
    account_email = models.EmailField(blank=True, null=True)

    REQUESTED_ACCESS_DURATION_CHOICES = (
        # Translators: One of four choices users can choose from as the preferred duration of how long they would like their access to a particular resource to last. 1 month in this case.
        (1, _("1 month")),
        # Translators: One of four choices users can choose from as the preferred duration of how long they would like their access to a particular resource to last. 3 months in this case.
        (3, _("3 months")),
        # Translators: One of four choices users can choose from as the preferred duration of how long they would like their access to a particular resource to last. 6 months in this case.
        (6, _("6 months")),
        # Translators: One of four choices users can choose from as the preferred duration of how long they would like their access to a particular resource to last. 12 months in this case.
        (12, _("12 months")),
    )

    requested_access_duration = models.IntegerField(
        choices=REQUESTED_ACCESS_DURATION_CHOICES,
        blank=True,
        null=True,
        help_text="User selection of when they'd like their account to expire (in months). "
        "Required for proxied resources; optional otherwise.",
    )

    # Was this application imported via CLI?
    imported = models.BooleanField(default=False, null=True)

    # If this Application is a renewal, the parent is the original Application
    # it was copied from.
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True)
    waitlist_status = models.BooleanField(
        default=False, help_text="Mark as True if the partner is WAITLISTED"
    )

    def __str__(self):
        return "{self.editor} - {self.partner}".format(self=self)

    def get_absolute_url(self):
        return reverse_lazy("applications:evaluate", kwargs={"pk": self.pk})

    def get_status_display(self):

        if (
            self.status == self.SENT
            and self.partner.authorization_method != self.partner.EMAIL
        ):
            # Translators: This is the status of an application that has been finalized upon approval.
            return _("Finalized")

        return self.STATUS_CHOICES[self.status][1]

    # Every single save to this model should create a revision.
    # You can access two models this way: REVISIONS and VERSIONS.
    # Versions contain the model data at the time, accessible via
    # version.field_dict['field_name']. Revisions contain metadata about the
    # version (like when it was saved).
    # See http://django-reversion.readthedocs.io/en/stable.
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
            data = model_to_dict(
                self,
                fields=[
                    "rationale",
                    "specific_title",
                    "comments",
                    "agreement_with_terms_of_use",
                ],
            )

            # Status and parent are explicitly different on the child than
            # on the parent application. For editor and partner, we
            # need to pull those directly - model_to_dict will give us the pks
            # of the referenced objects, but we need the actual objects.
            data.update(
                {
                    "status": self.PENDING,
                    "parent": self,
                    "editor": self.editor,
                    "partner": self.partner,
                    "account_email": self.account_email,
                    "requested_access_duration": self.requested_access_duration,
                }
            )

            # Create clone. We can't use the normal approach of setting the
            # object's pk to None and then saving it, because the object in
            # this case is 'self', and weird things happen.
            clone = Application(**data)
            clone.save()

            return clone

    LABELMAKER = {
        PENDING: "-primary",
        INVALID: "-danger",
        QUESTION: "-warning",
        APPROVED: "-success",
        NOT_APPROVED: "-danger",
        SENT: "-success",
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
            assert self.status in [
                self.APPROVED,
                self.NOT_APPROVED,
                self.SENT,
                self.INVALID,
            ]
            return (self.date_closed - self.date_created).days

    def get_user_instructions(self):
        """
        This application will either be to a partner or collection. If the
        former, this function returns the partner user instructions. Otherwise,
        it gets the user instructions for this collection.
        """
        user_instructions = None
        resource = None
        if self.partner:
            resource = self.partner

        # Fetch instructions from the database if appropriate
        if resource:
            if (
                resource.authorization_method in [Partner.CODES, Partner.LINK]
                and resource.user_instructions
            ):
                user_instructions = resource.user_instructions
            elif (
                resource.authorization_method == Partner.PROXY
                and resource.get_access_url
            ):
                # fmt: off
                # Translators: This text goes into account approval emails in the case that we need to send the user a programmatically generated link to a resource.
                user_instructions = _("Access URL: {access_url}")\
                    .format(access_url=resource.get_access_url)
                # fmt: on
            else:
                # fmt: off
                # Translators: This text goes into account approval emails in the case that we need to send the user's details to a publisher for manual account setup.
                user_instructions = _("You can expect to receive access details within a week or two once it has been processed.")
                # fmt: on
        return user_instructions

    def get_authorization(self):
        """
        For a given application, find an authorization for this partner-editor, if possible.
        """
        try:
            authorization = Authorization.objects.get(
                partners=self.partner, user=self.editor.user
            )
        except Authorization.DoesNotExist:
            return None

        return authorization

    def is_instantly_finalized(self):
        """
        Check if this application is to a partner or collection for which
        we will instantly mark it as finalized and provide access.
        """
        instantly_finalised_authorization_methods = [Partner.PROXY, Partner.LINK]
        authorization_method = self.partner.authorization_method

        if authorization_method in instantly_finalised_authorization_methods:
            return True
        else:
            return False

    @property
    def user(self):
        """
        Needed by PartnerCoordinatorOrSelf mixin, e.g. on the application evaluation view.
        """
        return self.editor.user

    @property
    def is_renewable(self):
        """
        Apps are eligible for renewal if they are approved/sent and have not already
        been renewed.
        """
        return all(
            [
                not bool(Application.objects.filter(parent=self)),
                self.status in [self.APPROVED, self.SENT],
                self.partner.renewals_available,
            ]
        )
