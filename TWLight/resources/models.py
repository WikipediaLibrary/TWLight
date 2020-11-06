# -*- coding: utf-8 -*-
import copy

from taggit.managers import TaggableManager
from taggit.models import TagBase, GenericTaggedItemBase

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy, reverse
from django.db import models
from django_countries.fields import CountryField

from TWLight.resources.helpers import (
    check_for_target_url_duplication_and_generate_error_message,
)

RESOURCE_LANGUAGES = copy.copy(settings.INTERSECTIONAL_LANGUAGES)

RESOURCE_LANGUAGE_CODES = [lang[0] for lang in RESOURCE_LANGUAGES]


def validate_language_code(code):
    """
    Takes a language code and verifies that it is the first element of a tuple
    in RESOURCE_LANGUAGES.
    """
    if code not in RESOURCE_LANGUAGE_CODES:
        raise ValidationError(
            "%(code)s is not a valid language code. You must enter an ISO "
            "language code, as in the INTERSECTIONAL_LANGUAGES setting at "
            "https://github.com/WikipediaLibrary/TWLight/blob/master/TWLight/settings/base.py",
            params={"code": code},
        )


class TextFieldTag(TagBase):
    """
    We're defining a custom tag here the following reasons:
    * Without doing so, the migrations that define our tags end up in the taggit
      apps migration folder instead of ours, making version control difficult.
    * So we can use a non-unique Text field for the tag name. This is done to
      prevent indexing, because translations can cause the number of indexes to
      exceed the limits of any storage engine available to MySQL/MariaDB.
      Avoiding indexes has consequences.
    Docs here: https://django-taggit.readthedocs.io/en/latest/custom_tagging.html#using-a-custom-tag-or-through-model
    """

    name = models.TextField(verbose_name="Name", unique=False, max_length=100)
    slug = models.SlugField(verbose_name="Slug", unique=True, max_length=100)
    meta_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link to Meta-Wiki "
        "(eg.: https://meta.wikimedia.org/wiki/The_Wikipedia_Library/Collections/Agroforestry) "
        "for additional information for this tag.",
    )

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"


class TaggedTextField(GenericTaggedItemBase):
    tag = models.ForeignKey(
        TextFieldTag,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )


class Language(models.Model):
    """
    We want to be able to indicate the language(s) of resources offered by a
    Partner or in a Stream.

    While having a standalone model is kind of overkill, it offers the
    following advantages:
    * We need to be able to indicate multiple languages for a given Partner or
      Stream.
    * We will want to be able to filter Partners and Streams by language (e.g.
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
        max_length=8,
        validators=[validate_language_code],
        unique=True,
        default=RESOURCE_LANGUAGES[16]
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

    # Authorization methods, used in both Partner and Stream
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
        help_text="Add the number of new accounts to the existing value, not by resetting it to zero. If 'specific stream' is true, change accounts availability at the collection level.",
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

    short_description = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Optional short description of this partner's resources.",
    )

    description = models.TextField(
        "long description",
        blank=True,
        help_text="Optional detailed description in addition to the short "
        "description such as collections, instructions, notes, special "
        "requirements, alternate access options, unique features, citations notes.",
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

    mutually_exclusive = models.NullBooleanField(
        blank=True,
        null=True,
        default=None,
        help_text="If True, users can only apply for one Stream at a time "
        "from this Partner. If False, users can apply for multiple Streams at "
        "a time. This field must be filled in when Partners have multiple "
        "Streams, but may be left blank otherwise.",
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

    tags = TaggableManager(through=TaggedTextField, blank=True)

    # This field has to stick around until all servers are using the new tags.
    old_tags = TaggableManager(through=None, blank=True, verbose_name="Old Tags")

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
    specific_stream = models.BooleanField(
        default=False,
        help_text="Mark as true if this partner requires applicants to "
        "specify the database they want to access.",
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

    def clean(self):
        if self.agreement_with_terms_of_use and not self.terms_of_use:
            raise ValidationError(
                "When agreement with terms of use is "
                "required, a link to terms of use must be provided."
            )
        if self.streams.count() > 1:
            if self.mutually_exclusive is None:
                raise ValidationError(
                    "Since this resource has multiple "
                    "Streams, you must specify a value for mutually_exclusive."
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
            # all PROXY and BUNDLE partners/streams.
            validation_error_msg = (
                check_for_target_url_duplication_and_generate_error_message(
                    self, partner=True
                )
            )
            if validation_error_msg:
                raise ValidationError({"target_url": validation_error_msg})

    def get_absolute_url(self):
        return reverse_lazy("partners:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        super(Partner, self).save(*args, **kwargs)
        """Invalidate this partner's pandoc-rendered html from cache"""
        for code in RESOURCE_LANGUAGE_CODES:
            short_description_cache_key = make_template_fragment_key(
                "partner_short_description", [code, self.pk]
            )
            description_cache_key = make_template_fragment_key(
                "partner_description", [code, self.pk]
            )
            send_instructions_cache_key = make_template_fragment_key(
                "partner_send_instructions", [code, self.pk]
            )
            cache.delete(short_description_cache_key)
            cache.delete(description_cache_key)
            cache.delete(send_instructions_cache_key)

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


class PartnerLogo(models.Model):
    partner = models.OneToOneField(
        "Partner", related_name="logos", on_delete=models.CASCADE
    )
    logo = models.ImageField(
        blank=True,
        null=True,
        help_text="Optional image file that can be used to represent this " "partner.",
    )


class Stream(models.Model):
    """
    A specific resource provided by a partner organization, when they offer
    multiple resources that require separate applications. Example: Elsevier's
    Health & Life Sciences collection, which is distinct from its Social &
    Behavioral Sciences collection.

    At present, Streams have no information other than their name and Partner
    (and an optional description). However, separating them in the database
    will make it easier to cope in future should partners start expecting
    different application information for different Streams, or if they have
    distinct contact information, et cetera.
    """

    class Meta:
        app_label = "resources"
        verbose_name = "collection"
        verbose_name_plural = "collections"
        ordering = ["partner", "name"]

    partner = models.ForeignKey(
        Partner, db_index=True, related_name="streams", on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=50,
        help_text="Name of stream (e.g. 'Health and Behavioral Sciences). "
        "Will be user-visible and *not translated*. Do not include the "
        "name of the partner here.",
    )

    accounts_available = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Add number of new accounts to the existing value, not by reseting it to zero.",
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of this stream's resources.",
    )

    languages = models.ManyToManyField(Language, blank=True)

    authorization_method = models.IntegerField(
        choices=Partner.AUTHORIZATION_METHODS,
        default=Partner.EMAIL,
        help_text="Which authorization method does this collection use? "
        "'Email' means the accounts are set up via email, and is the default. "
        "Select 'Access Codes' if we send individual, or group, login details "
        "or access codes. 'Proxy' means access delivered directly via EZProxy, "
        "and Library Bundle is automated proxy-based access. 'Link' is if we "
        "send users a URL to use to create an account.",
    )

    target_url = models.URLField(
        blank=True,
        null=True,
        help_text="Link to collection. Required for proxied collections; optional otherwise.",
    )

    user_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Optional instructions for editors to use access codes "
        "or free signup URLs for this collection. Sent via email upon "
        "application approval (for links) or access code assignment.",
    )

    def __str__(self):
        # Do not try to also return the partner name here (e.g.
        # "Partnername: Streamname") because that will be hard to
        # internationalize. Returning the atomic stream name gives us more
        # options for how this is displayed in templates.
        return self.name

    def clean(self):
        if self.target_url:
            # Validate the form for the uniqueness of self.target_url across
            # all PROXY and BUNDLE partners/streams.
            validation_error_msg = (
                check_for_target_url_duplication_and_generate_error_message(
                    self, stream=True
                )
            )
            if validation_error_msg:
                raise ValidationError({"target_url": validation_error_msg})

    def save(self, *args, **kwargs):
        """Invalidate the rendered html stream description from cache"""
        super(Stream, self).save(*args, **kwargs)
        for code in RESOURCE_LANGUAGE_CODES:
            cache_key = make_template_fragment_key(
                "stream_description", [code, self.pk]
            )
            cache.delete(cache_key)

    @property
    def get_languages(self):
        return ", ".join([p.__str__() for p in self.languages.all()])

    @property
    def get_access_url(self):
        ezproxy_url = settings.TWLIGHT_EZPROXY_URL
        access_url = None
        if (
            self.authorization_method in [Partner.PROXY, Partner.BUNDLE]
            and ezproxy_url
            and self.target_url
        ):
            access_url = ezproxy_url + "/login?url=" + self.target_url
        elif self.target_url:
            access_url = self.target_url
        return access_url


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
        # As with Stream, do not return the partner name here.
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
