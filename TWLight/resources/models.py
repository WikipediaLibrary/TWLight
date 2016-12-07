# -*- coding: utf-8 -*-

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.utils.translation  import ugettext_lazy as _

from durationfield.db.models.fields.duration import DurationField


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
        help_text=_("Optional description of this partner's offerings."))
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

    # See comment in save().
    access_grant_term = DurationField(
        blank=True, null=True,
        help_text=_("The standard length of an access grant from this Partner. "
                    "Enter like '365 days' or '365d' or '1 year'.")
        )


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


    def save(self, *args, **kwargs):
        if not self.access_grant_term:
            # We can't declare a default access grant term in the ORM due to a
            # bug not fixed in Django until 1.8:
            # https://code.djangoproject.com/ticket/24566
            # However, code elsewhere expects the access grant term to exist.
            # So we will make sure it happens on model save.
            self.access_grant_term = timedelta(days=365)
        super(Partner, self).save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse_lazy('partners:detail', kwargs={'pk': self.pk})



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
        help_text=_("Optional description of this stream's contents."))


    def __unicode__(self):
        # Do not try to also return the partner name here (e.g.
        # "Partnername: Streamname") because that will be hard to
        # internationalize. Returning the atomic stream name gives us more
        # options for how this is displayed in templates.
        return self.name



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

    title = models.CharField(max_length=30,
        help_text=_("Organizational role or job title. This is NOT intended "
        "to be used for honorifics."))
    email = models.EmailField()
    full_name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=15,
        help_text=_("The form of the contact person's name to use in email "
        "greetings (as in 'Hi Jake')"))


    def __unicode__(self):
        # As with Stream, do not return the partner name here.
        return self.full_name
