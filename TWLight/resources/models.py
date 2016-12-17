# -*- coding: utf-8 -*-
import copy
from datetime import timedelta

from django.conf.global_settings import LANGUAGES
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.utils.translation  import ugettext_lazy as _

from durationfield.db.models.fields.duration import DurationField

RESOURCE_LANGUAGES = copy.copy(LANGUAGES)

RESOURCE_LANGUAGE_CODES = [lang[0] for lang in RESOURCE_LANGUAGES]

def validate_language_code(code):
    """
    Takes a language code and verifies that it is the first element of a tuple
    in RESOURCE_LANGUAGES.
    """
    if code not in RESOURCE_LANGUAGE_CODES:
        raise ValidationError(
            _('%(code)s is not a valid language code. You must enter an ISO '
                'language code, as in the LANGUAGES setting at '
                'https://github.com/django/django/blob/master/django/conf/global_settings.py'),
            params={'code': code},
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
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    language = models.CharField(choices=RESOURCE_LANGUAGES,
        max_length=8,
        validators=[validate_language_code],
        unique=True
        )

    def save(self, *args, **kwargs):
        """Cause validator to be run."""
        self.clean_fields()
        super(Language, self).save(*args, **kwargs)


    def __unicode__(self):
        return self.get_language_display()



class AvailablePartnerManager(models.Manager):
    def get_queryset(self):
        return super(AvailablePartnerManager, self).get_queryset(
            ).filter(status=Partner.AVAILABLE)


class Partner(models.Model):
    """
    A partner organization which provides access grants to paywalled resources.
    This model tracks contact information for the partner as well as extra
    information they require on access grant applications.
    """
    class Meta:
        app_label = 'resources'
        verbose_name = 'partner'
        verbose_name_plural = 'partners'
        ordering = ['company_name']

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

    company_name = models.CharField(max_length=40,
        help_text=_("Partner organization's name (e.g. McFarland). Note: "
        "this will be user-visible and *not translated*."))
    date_created = models.DateField(auto_now_add=True)

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

    STATUS_CHOICES = (
        # Translators: This is a status for a Partner, denoting that editors can apply for access.
        (AVAILABLE, _('Available')),
        # Translators: This is a status for a Partner, denoting that editors cannot apply for access and the Partner will not be displayed to them.
        (NOT_AVAILABLE, _('Not available')),
    )

    status = models.IntegerField(choices=STATUS_CHOICES,
        default=NOT_AVAILABLE,
        help_text=_('Should this Partner be displayed to end users? Is it '
                    'open for applications right now?'))

    # Optional resource metadata
    # --------------------------------------------------------------------------

    terms_of_use = models.URLField(blank=True, null=True,
        help_text=_("Link to terms of use. Required if this company requires "
            "that users agree to terms of use as a condition of applying for "
            "access; optional otherwise."))
    description = models.TextField(blank=True, null=True,
        help_text=_("Optional description of this partner's offerings. You can "
            "enter HTML and it should render properly - if it does not, the "
            "developer forgot a | safe filter in the template."))
    logo_url = models.URLField(blank=True, null=True,
        help_text=_('Optional URL of an image that can be used to represent '
                    'this partner.'))

    mutually_exclusive = models.NullBooleanField(
        blank=True, null=True,
        default=None,
        help_text=_("If True, users can only apply for one Stream at a time "
        "from this Partner. If False, users can apply for multiple Streams at "
        "a time. This field must be filled in when Partners have multiple "
        "Streams, but may be left blank otherwise."))

    access_grant_term = models.DurationField(
        blank=True, null=True,
        default=timedelta(days=365),
        help_text=_("The standard length of an access grant from this Partner. "
            "Entered as <days hours:minutes:seconds>. Defaults to 365 days.")
        )

    languages = models.ManyToManyField(Language, blank=True, null=True)


    # Non-universal form fields
    # --------------------------------------------------------------------------

    # Some fields are required by all resources for all access grants.
    # Some fields are only required by some resources. This is where we track
    # whether *this* resource requires those optional fields.

    real_name = models.BooleanField(default=False,
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify their real names.'))
    country_of_residence = models.BooleanField(default=False,
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify their countries of residence.'))
    specific_title = models.BooleanField(default=False,
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify a particular title they want to access.'))
    specific_stream = models.BooleanField(default=False,
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify a particular database they want to access.'))
    occupation = models.BooleanField(default=False,
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify their occupation.'))
    affiliation = models.BooleanField(default=False,
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify their institutional affiliation.'))
    agreement_with_terms_of_use = models.BooleanField(default=False,
        help_text=_("Mark as true if this partner requires applicants to agree "
                    "with the partner's terms of use."))


    def __unicode__(self):
        return self.company_name


    def clean(self):
        if self.agreement_with_terms_of_use and not self.terms_of_use:
            raise ValidationError('When agreement with terms of use is '
                'required, a link to terms of use must be provided.')
        if self.streams.count() > 1:
            if self.mutually_exclusive is None:
                raise ValidationError('Since this resource has multiple '
                    'Streams, you must specify a value for mutually_exclusive.')


    def get_absolute_url(self):
        return reverse_lazy('partners:detail', kwargs={'pk': self.pk})


    @property
    def get_languages(self):
        return ", ".join([p.__unicode__() for p in self.languages.all()])



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
        app_label = 'resources'
        verbose_name = 'collection'
        verbose_name_plural = 'collections'
        ordering = ['partner', 'name']


    partner = models.ForeignKey(Partner, db_index=True, related_name="streams")
    name = models.CharField(max_length=50,
        help_text=_("Name of stream (e.g. 'Health and Behavioral Sciences). "
            "Will be user-visible and *not translated*. Do not include the "
            "name of the partner here. If partner name and resource name "
            "need to be presented together, templates are responsible for "
            "presenting them in a format that can be internationalized."))
    description = models.TextField(blank=True, null=True,
        help_text=_("Optional description of this stream's contents. You can "
            "enter HTML and it should render properly - if it does not, the "
            "developer forgot a | safe filter in the template."))

    languages = models.ManyToManyField(Language, blank=True, null=True)


    def __unicode__(self):
        # Do not try to also return the partner name here (e.g.
        # "Partnername: Streamname") because that will be hard to
        # internationalize. Returning the atomic stream name gives us more
        # options for how this is displayed in templates.
        return self.name

    @property
    def get_languages(self):
        return ", ".join([p.__unicode__() for p in self.languages.all()])



class Contact(models.Model):
    """
    A Partner may have one or more contact people. Most of this information is
    managed elsewhere through a CRM, but this app needs to know just enough to
    send emails and tell coordinators whom they're dealing with.
    """
    class Meta:
        app_label = 'resources'
        verbose_name = 'contact person'
        verbose_name_plural = 'contact people'


    partner = models.ForeignKey(Partner, db_index=True, related_name="contacts")

    title = models.CharField(max_length=75,
        help_text=_("Organizational role or job title. This is NOT intended "
        "to be used for honorifics. Think 'Director of Editorial Services', "
        "not 'Ms.'"))
    email = models.EmailField()
    full_name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=15,
        help_text=_("The form of the contact person's name to use in email "
        "greetings (as in 'Hi Jake')"))


    def __unicode__(self):
        # As with Stream, do not return the partner name here.
        return self.full_name
