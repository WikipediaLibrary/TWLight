# -*- coding: utf-8 -*-
import json
import os

from jsonschema import validate
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy, reverse
from django.db import models
from django_countries.fields import CountryField
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from TWLight.resources.helpers import (
    check_for_target_url_duplication_and_generate_error_message,
    get_tags_json_schema,
)

# Use language autonyms from Wikimedia.
# We periodically pull:
# https://raw.githubusercontent.com/wikimedia/language-data/master/data/language-data.json
# into locale/language-data.json
language_data_json = open(os.path.join(settings.LOCALE_PATHS[0], "language-data.json"))
languages = json.loads(language_data_json.read())["languages"]
RESOURCE_LANGUAGES = []
for lang_code, lang_data in languages.items():
    autonym = lang_data[-1]
    RESOURCE_LANGUAGES += [(lang_code, autonym)]

RESOURCE_LANGUAGE_CODES = [lang[0] for lang in RESOURCE_LANGUAGES]


def validate_language_code(code):
    """
    Takes a language code and verifies that it is the first element of a tuple
    in RESOURCE_LANGUAGES.
    """
    if code not in RESOURCE_LANGUAGE_CODES:
        raise ValidationError(
            "%(code)s is not a valid language code. You must enter an ISO "
            "language code, as in the LANGUAGES setting at "
            "https://github.com/WikipediaLibrary/TWLight/blob/master/TWLight/settings/base.py",
            params={"code": code},
        )


class Language(models.Model):
    """
    We want to be able to indicate the language(s) of resources offered by a
    Partner.

    While having a standalone model is kind of overkill, it offers the
    following advantages:
    * We need to be able to indicate multiple languages for a given Partner.
    * We will want to be able to filter Partners by language (e.g.
      in order to limit to the user's preferred language); we can't do that
      efficiently with something like django-multiselect or django-taggit.
    * In order to be able to filter by language, we also need to use a
      controlled vocabulary which we can validate; using a model makes this
      easy.
        * We default to Django's global LANGUAGES setting, which is extensive
          and already translated. We can always expand it if we find ourselves
          needing more languages, though.
    """

    class Meta:
        verbose_name = "Language"
        verbose_name_plural = "Languages"

    language = models.CharField(
        choices=RESOURCE_LANGUAGES,
        max_length=12,
        validators=[validate_language_code],
        unique=True,
    )

    def save(self, *args, **kwargs):
        """Cause validator to be run."""
        self.clean_fields()
        super(Language, self).save(*args, **kwargs)

    def __str__(self):
        return self.get_language_display()


class AvailablePartnerManager(models.Manager):
    def get_queryset(self):
        return (
            super(AvailablePartnerManager, self)
            .get_queryset()
            .filter(status__in=[Partner.AVAILABLE, Partner.WAITLIST])
        )


class Partner(models.Model):
    """
    A partner organization which provides access grants to paywalled resources.
    This model tracks contact information for the partner as well as extra
    information they require on access grant applications.
    """

    class Meta:
        app_label = "resources"
        verbose_name = "partner"
        verbose_name_plural = "partners"
        ordering = ["company_name"]

    # --------------------------------------------------------------------------
    # Managers
    # --------------------------------------------------------------------------

    # Define managers. Note that the basic manager must be first to make
    # Django internals work as expected, but we define objects as our custom
    # manager so that we don't inadvertently expose unavailable Partners to
    # end users.
    even_not_available = models.Manager()
    objects = AvailablePartnerManager()

    # --------------------------------------------------------------------------
    # Attributes
    # --------------------------------------------------------------------------

    company_name = models.CharField(
        max_length=255,
        help_text="Partner's name (e.g. McFarland). Note: "
        "this will be user-visible and *not translated*.",
    )
    date_created = models.DateField(auto_now_add=True)
    coordinator = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The coordinator for this Partner, if any.",
    )
    featured = models.BooleanField(
        default=False,
        help_text="Mark as true to feature this partner on the front page.",
    )
    company_location = CountryField(null=True, help_text="Partner's primary location.")

    # Status metadata
    # --------------------------------------------------------------------------
    # AVAILABLE partners are displayed to users.
    # NOT AVAILABLE partners are only accessible through the admin interface.
    # These may be, e.g., partners TWL used to work with but no longer does
    # (kept in the database for recordkeeping), or they may be partners TWL
    # is setting up a relationship with but isn't ready to expose to public
    # view.
    # We default to NOT_AVAILABLE to avoid inadvertently exposing Partners to
    # the application process when they're not ready yet, and to give staff
    # a chance to build their record incrementally and fix errors.
    AVAILABLE = 0
    NOT_AVAILABLE = 1
    WAITLIST = 2

    STATUS_CHOICES = (
        (AVAILABLE, "Available"),
        (NOT_AVAILABLE, "Not available"),
        (WAITLIST, "Waitlisted"),
    )

    # Authorization methods
    EMAIL = 0
    CODES = 1
    PROXY = 2
    BUNDLE = 3
    LINK = 4

    AUTHORIZATION_METHODS = (
        (EMAIL, "Email"),
        (CODES, "Access codes"),
        (PROXY, "Proxy"),
        (BUNDLE, "Library Bundle"),
        (LINK, "Link"),
    )

    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=NOT_AVAILABLE,
        help_text="Should this Partner be displayed to users? Is it "
        "open for applications right now?",
    )

    renewals_available = models.BooleanField(
        default=False,
        help_text="Can access grants to this partner be renewed? If so, "
        "users will be able to request renewals at any time.",
    )

    accounts_available = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Add the number of new accounts to the existing value, not by resetting it to zero.",
    )

    # Optional resource metadata
    # --------------------------------------------------------------------------
    target_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link to partner resources. Required for proxied resources; optional otherwise.",
    )

    terms_of_use = models.URLField(
        blank=True,
        null=True,
        help_text="Link to terms of use. Required if users must agree to "
        "terms of use to get access; optional otherwise.",
    )

    send_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Optional instructions for sending application data to "
        "this partner.",
    )

    user_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Optional instructions for editors to use access codes "
        "or free signup URLs for this partner. Sent via email upon "
        "application approval (for links) or access code assignment. "
        "If this partner has collections, fill out user instructions "
        "on each collection instead.",
    )

    excerpt_limit = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Optional excerpt limit in terms of number of words per article. Leave empty if no limit.",
    )

    excerpt_limit_percentage = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MaxValueValidator(100)],
        help_text="Optional excerpt limit in terms of percentage (%) of an article. Leave empty if no limit.",
    )

    authorization_method = models.IntegerField(
        choices=AUTHORIZATION_METHODS,
        default=EMAIL,
        help_text="Which authorization method does this partner use? "
        "'Email' means the accounts are set up via email, and is the default. "
        "Select 'Access Codes' if we send individual, or group, login details "
        "or access codes. 'Proxy' means access delivered directly via EZProxy, "
        "and Library Bundle is automated proxy-based access. 'Link' is if we "
        "send users a URL to use to create an account.",
    )

    languages = models.ManyToManyField(
        Language,
        blank=True,
        help_text="Select all languages in which this partner publishes " "content.",
    )

    account_length = models.DurationField(
        blank=True,
        null=True,
        help_text="The standard length of an access grant from this Partner. "
        "Entered as &ltdays hours:minutes:seconds&gt.",
    )

    # New tag model that uses JSONField instead of Taggit to make tags translatable

    new_tags = models.JSONField(
        null=True,
        default=None,
        blank=True,
        help_text="Tag must be a valid JSON schema. Tag should be in the form of tag-name_tag.",
    )

    # Searchable status of a partner
    SEARCHABLE = 0
    NOT_SEARCHABLE = 1
    PARTIALLY_SEARCHABLE = 2

    SEARCHABLE_CHOICES = (
        # Translators: This indicates that a collection included in the centralized search tool (https://meta.wikimedia.org/wiki/Talk:Library_Card_platform/Search)
        (SEARCHABLE, _("Searchable")),
        # Translators: This indicates that a collection is excluded from the centralized search tool (https://meta.wikimedia.org/wiki/Talk:Library_Card_platform/Search)
        (NOT_SEARCHABLE, _("Not searchable")),
        # Translators: This indicates that a collection is partially included in the centralized search tool (https://meta.wikimedia.org/wiki/Talk:Library_Card_platform/Search)
        (PARTIALLY_SEARCHABLE, _("Partially searchable")),
    )

    searchable = models.IntegerField(
        choices=SEARCHABLE_CHOICES,
        default=NOT_SEARCHABLE,
        help_text="Indicates whether a partner is searchable in EDS or not.",
    )

    # Non-universal form fields
    # --------------------------------------------------------------------------

    # Some fields are required by all resources for all access grants.
    # Some fields are only required by some resources. This is where we track
    # whether *this* resource requires those optional fields.

    registration_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link to registration page. Required if users must sign up "
        "on the partner's website in advance; optional otherwise.",
    )
    real_name = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicant names.",
    )
    country_of_residence = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicant countries "
        "of residence.",
    )
    specific_title = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicants to "
        "specify the title they want to access.",
    )
    occupation = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicants to "
        "specify their occupation.",
    )
    affiliation = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicants to "
        "specify their institutional affiliation.",
    )
    agreement_with_terms_of_use = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicants to agree "
        "with the partner's terms of use.",
    )
    account_email = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicants to have "
        "already signed up at the partner website.",
    )

    # Integrating a dropdown field to get the duration for which a user wishes to have his/her
    # access for without this boolean field isn't a problem for renewals. We want this
    # field to get along with the initial dynamic application form generation (applications/forms.py).
    # The way these optional fields (to get input from users) work, when different partners have
    # different requirements, optional or not is decided by these boolean fields. We could've
    # worked around that by checking the authorization_method, but not without a significant amount
    # of rework. This is plain and simple and adds one more teeny tiny step for superusers. As it
    # happens, this also gives us the unintended advantage of toggling the field on even when the
    # partner doesn't have proxy, but has account durations that can be manually set.
    requested_access_duration = models.BooleanField(
        default=False,
        help_text="Must be checked if the authorization method of this partner is proxy; "
        "optional otherwise.",
    )

    def __str__(self):
        return self.company_name

    def clean(self, *args, **kwargs):
        if self.agreement_with_terms_of_use and not self.terms_of_use:
            raise ValidationError(
                "When agreement with terms of use is "
                "required, a link to terms of use must be provided."
            )
        if self.account_email and not self.registration_url:
            raise ValidationError(
                "When pre-registration is required, "
                "a link to the registration page must be provided."
            )
        if (
            self.authorization_method == self.PROXY
            and not self.requested_access_duration
        ):
            raise ValidationError(
                {
                    "requested_access_duration": [
                        "When authorization method is proxy, "
                        "requested_access_duration field must be checked."
                    ]
                }
            )
        if self.target_url:
            # Validate the form for the uniqueness of self.target_url across
            # all PROXY and BUNDLE partners.
            validation_error_msg = (
                check_for_target_url_duplication_and_generate_error_message(
                    self, partner=True
                )
            )
            if validation_error_msg:
                raise ValidationError({"target_url": validation_error_msg})

        if self.authorization_method in [self.CODES, self.LINK] and (
            not self.user_instructions
        ):
            raise ValidationError(
                "Partners with automatically sent messages require user instructions to be entered"
            )
        if self.authorization_method in [self.PROXY, self.BUNDLE]:
            # Validate that target_url should not be empty
            # when authorization method is PROXY or BUNDLE
            if not self.target_url:
                raise ValidationError("Proxy and Bundle partners require a target URL.")

        # If new_tags is not empty, validate with JSONSchema
        if self.new_tags is not None:
            try:
                validate(
                    instance=self.new_tags,
                    schema=get_tags_json_schema(),
                )
            except JSONSchemaValidationError:
                raise ValidationError(
                    mark_safe(
                        "Error trying to insert a tag: please choose a tag from <a rel='noopener' target='_blank' href='https://github.com/WikipediaLibrary/TWLight/blob/production/locale/en/tag_names.json'>tag_names.json</a>."
                    )
                )

    def get_absolute_url(self):
        return reverse_lazy("partners:detail", kwargs={"pk": self.pk})

    @property
    def get_languages(self):
        return self.languages.all()

    @property
    def is_waitlisted(self):
        return self.status == self.WAITLIST

    @property
    def is_not_available(self):
        return self.status == self.NOT_AVAILABLE

    @property
    def get_access_url(self):
        ezproxy_url = settings.TWLIGHT_EZPROXY_URL
        ezproxy_auth = settings.TWLIGHT_ENV
        access_url = None
        if (
            self.authorization_method in [self.PROXY, self.BUNDLE]
            and ezproxy_url
            and ezproxy_auth
            and self.target_url
        ):
            access_url = (
                ezproxy_url + "/login?auth=" + ezproxy_auth + "&url=" + self.target_url
            )
        elif self.target_url:
            access_url = self.target_url
        return access_url

    @property
    def phab_task_qs(self):
        return PhabricatorTask.objects.filter(partners__pk=self.pk).order_by(
            "-task_type"
        )


class PartnerLogo(models.Model):
    partner = models.OneToOneField(
        "Partner", related_name="logos", on_delete=models.CASCADE
    )
    logo = models.ImageField(
        blank=True,
        null=True,
        help_text="Optional image file that can be used to represent this " "partner.",
    )


class PhabricatorTask(models.Model):
    class Meta:
        verbose_name = "Phabricator Task"
        verbose_name_plural = "Phabricator Tasks"

    partners = models.ManyToManyField(
        Partner,
        blank=True,
        # Limit to available partners.
        help_text="The partner(s) affected by this task.",
    )

    INFO = 0
    WARNING = 1
    DANGER = 2

    TYPE_CHOICES = (
        # Translators: Expandable element with information about the status of this partner
        (INFO, _("Service information")),
        # Translators: Expandable element with information about the status of this partner
        (WARNING, _("Service issue")),
        # Translators: Expandable element with information about the status of this partner
        (DANGER, _("Temporarily unavailable")),
    )

    TYPE_HELP = (
        # Translators: information about the current status of this partner
        (INFO, _("Ongoing work may impact access")),
        # Translators: information about a current issue with this partner
        (WARNING, _("An issue is impacting access")),
        # Translators: information about a current outage for this partner
        (DANGER, _("Access is currently unavailable")),
    )

    TYPE_SEVERITY = (
        (INFO, "info"),
        (WARNING, "warning"),
        (DANGER, "danger"),
    )

    task_type = models.IntegerField(
        choices=TYPE_CHOICES,
        default=INFO,
        help_text="Will linking this task inform them of ongoing changes, warn them of issues impacting some users, or indicate an outage?",
    )

    phabricator_task = models.CharField(
        max_length=255, help_text="Phabricator Task ID, eg. T314780"
    )

    @property
    def url(self):
        return "https://phabricator.wikimedia.org/" + self.phabricator_task

    @property
    def task_display(self):
        return (
            self.TYPE_CHOICES[self.task_type][1],
            self.TYPE_SEVERITY[self.task_type][1],
            self.TYPE_HELP[self.task_type][1],
        )


class Contact(models.Model):
    """
    A Partner may have one or more contact people. Most of this information is
    managed elsewhere through a CRM, but this app needs to know just enough to
    send emails and tell coordinators whom they're dealing with.
    """

    class Meta:
        app_label = "resources"
        verbose_name = "contact person"
        verbose_name_plural = "contact people"

    partner = models.ForeignKey(
        Partner, db_index=True, related_name="contacts", on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=75,
        blank=True,
        help_text="Organizational role or job title. This is NOT intended "
        "to be used for honorifics. Think 'Director of Editorial Services', "
        "not 'Ms.' Optional.",
    )
    email = models.EmailField()
    full_name = models.CharField(max_length=50)
    short_name = models.CharField(
        max_length=15,
        help_text="The form of the contact person's name to use in email "
        "greetings (as in 'Hi Jake')",
    )

    def __str__(self):
        # Do not return the partner name here.
        return self.full_name


class Suggestion(models.Model):
    class Meta:
        app_label = "resources"
        verbose_name = "suggestion"
        verbose_name_plural = "suggestions"
        ordering = ["suggested_company_name"]

    suggested_company_name = models.CharField(
        max_length=40, help_text="Potential partner's name (e.g. McFarland)."
    )

    description = models.TextField(
        blank=True,
        max_length=1000,
        help_text="Optional description of this potential partner.",
    )

    company_url = models.URLField(
        blank=True, null=True, help_text="Link to the potential partner's website."
    )

    author = models.ForeignKey(
        User,
        related_name="suggestion_author",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="User who authored this suggestion.",
    )

    upvoted_users = models.ManyToManyField(
        User, blank=True, help_text="Users who have upvoted this suggestion."
    )
    ticket_number = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="phabricator ticket id where we track progress of request",
    )

    def __str__(self):
        return self.suggested_company_name

    def get_absolute_url(self):
        return reverse("suggest")

    def get_upvote_url(self):
        return reverse("upvote", kwargs={"pk": self.pk})


class Video(models.Model):
    class Meta:
        app_label = "resources"
        verbose_name = "video tutorial"
        verbose_name_plural = "video tutorials"
        ordering = ["partner"]

    partner = models.ForeignKey(
        Partner, db_index=True, related_name="videos", on_delete=models.CASCADE
    )

    tutorial_video_url = models.URLField(
        blank=True, null=True, help_text="URL of a video tutorial."
    )


class AccessCode(models.Model):
    """
    Some partners distribute access via access codes which TWL staff hold.
    This model holds each access code, assigning them to a partner and later
    a user.
    """

    class Meta:
        app_label = "resources"
        verbose_name = "access code"
        verbose_name_plural = "access codes"

    partner = models.ForeignKey(
        Partner,
        db_index=True,
        related_name="accesscodes",
        limit_choices_to=(models.Q(authorization_method=1)),
        on_delete=models.CASCADE,
    )

    code = models.CharField(max_length=60, help_text="An access code for this partner.")

    # This syntax is required for the ForeignKey to avoid a circular
    # import between the authorizations and resources models
    authorization = models.OneToOneField(
        "users.Authorization",
        related_name="accesscodes",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
