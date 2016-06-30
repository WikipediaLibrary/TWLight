from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.db import models

from durationfield.db.models.fields.duration import DurationField


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


    company_name = models.CharField(max_length=30,
        help_text="Partner organization's name (e.g. McFarland). Note: " \
        "this will be user-visible and *not translated*.")
    date_created = models.DateField(auto_now_add=True)


    # Optional resource metadata
    # --------------------------------------------------------------------------

    terms_of_use = models.URLField(blank=True, null=True,
        help_text="Required if this company requires that users agree to " \
        "terms of use as a condition of applying for access; optional " \
        "otherwise.")
    description = models.TextField(blank=True, null=True,
        help_text="Optional description of this partner's offerings.")

    mutually_exclusive = models.NullBooleanField(
        blank=True, null=True,
        default=None,
        help_text="If True, users can only apply for one Stream at a time from "
        "this Partner. If False, users can apply for multiple Streams at a "
        "time. This field must be filled in when Partners have multiple "
        "Streams, but may be left blank otherwise.")

    # See comment in save().
    access_grant_term = DurationField(
        blank=True, null=True,
        help_text="The standard length of an access grant from this Partner. " \
                  "Enter like '365 days' or '365d' or '1 year'."
        )


    # Non-universal form fields
    # --------------------------------------------------------------------------

    # Some fields are required by all resources for all access grants.
    # Some fields are only required by some resources. This is where we track
    # whether *this* resource requires those optional fields.

    real_name = models.BooleanField(default=False)
    country_of_residence = models.BooleanField(default=False)
    specific_title = models.BooleanField(default=False)
    specific_stream = models.BooleanField(default=False)
    occupation = models.BooleanField(default=False)
    affiliation = models.BooleanField(default=False)
    agreement_with_terms_of_use = models.BooleanField(default=False)

    # TODO: information about access grant workflows and email templates


    def __str__(self):
        return self.company_name


    def save(self, *args, **kwargs):
        if not self.access_grant_term:
            # We can't declare a default access grant term in the ORM due to a
            # bug not fixed in Django until 1.8:
            # https://code.djangoproject.com/ticket/24566
            # However, code elsewhere expects the access grant term to exist.
            # So we will make sure it happens on model save.
            self.access_grant_term = timedelta(days=20)
        if self.agreement_with_terms_of_use and not self.terms_of_use:
            raise ValidationError('When agreement with terms of use is '
                'required, a link to terms of use must be provided.')
        if self.streams.count() > 1:
            if self.mutually_exclusive is None:
                raise ValidationError('Since this resource has multiple '
                    'Streams, you must specify a value for mutually_exclusive.')
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


    partner = models.ForeignKey(Partner, db_index=True, related_name="streams")
    name = models.CharField(max_length=50,
        help_text="Name of stream (e.g. 'Health and Behavioral Sciences). "
            "Will be user-visible and *not translated*. Do not include the "
            "name of the partner here. If partner name and resource name "
            "need to be presented together, templates are responsible for "
            "presenting them in a format that can be internationalized.")
    description = models.TextField(blank=True, null=True,
        help_text="Optional description of this stream's contents.")


    def __str__(self):
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
        help_text="Organizational role or job title. This is NOT intended "
        "to be used for honorofics.")
    email = models.EmailField()
    full_name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=15,
        help_text="The form of the contact person's name to use in email " \
        "greetings (as in 'Hi Jake')")


    def __str__(self):
        # As with Stream, do not return the partner name here.
        return self.full_name
