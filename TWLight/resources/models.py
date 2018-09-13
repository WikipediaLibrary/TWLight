# -*- coding: utf-8 -*-
import copy
from datetime import timedelta

from taggit.managers import TaggableManager
from taggit.models import TagBase, GenericTaggedItemBase

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.db import models
from django.utils.translation  import ugettext_lazy as _
from django_countries.fields import CountryField

RESOURCE_LANGUAGES = copy.copy(settings.INTERSECTIONAL_LANGUAGES)

RESOURCE_LANGUAGE_CODES = [lang[0] for lang in RESOURCE_LANGUAGES]

def validate_language_code(code):
    """
    Takes a language code and verifies that it is the first element of a tuple
    in RESOURCE_LANGUAGES.
    """
    if code not in RESOURCE_LANGUAGE_CODES:
        raise ValidationError(
            # Translators: When staff enter languages, they use ISO language codes. Don't translate ISO, LANGUAGES, or %(code)s.
            _('%(code)s is not a valid language code. You must enter an ISO '
                'language code, as in the INTERSECTIONAL_LANGUAGES setting at '
                'https://github.com/WikipediaLibrary/TWLight/blob/master/TWLight/settings/base.py'),
            params={'code': code},
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
    name = models.TextField(verbose_name=_('Name'), unique=False, max_length=100)
    slug = models.SlugField(verbose_name=_('Slug'), unique=True, max_length=100)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

class TaggedTextField(GenericTaggedItemBase):
    tag = models.ForeignKey(TextFieldTag,
                            related_name="%(app_label)s_%(class)s_items")

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
        # Translators: Title for a list of languages if there is only one.
        verbose_name = _("Language")
        # Translators: Title for a list of languages if there is more than one.
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
            ).filter(status__in=[Partner.AVAILABLE, Partner.WAITLIST])



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
        # Translators: In the administrator interface, this text is help text for a field where staff can enter the name of the partner. Don't translate McFarland.
        help_text=_("Partner's name (e.g. McFarland). Note: "
        "this will be user-visible and *not translated*."))
    date_created = models.DateField(auto_now_add=True)
    coordinator = models.ForeignKey(User, blank=True, null=True,
        on_delete=models.SET_NULL,
        # Translators: In the administrator interface, this text is help text for a field where staff can specify the username of the account coordinator for this partner.
        help_text=_('The coordinator for this Partner, if any.'))
    featured = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether a publisher will be featured on the website's front page.
        help_text=_("Mark as true to feature this partner on the front page."))
    company_location = CountryField(null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can enter the partner organisation's country.
        help_text=_("Partner's primary location."))

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
        # Translators: This is a status for a Partner, denoting that editors can apply for access.
        (AVAILABLE, _('Available')),
        # Translators: This is a status for a Partner, denoting that editors cannot apply for access and the Partner will not be displayed to them.
        (NOT_AVAILABLE, _('Not available')),
        # Translators: This is a status for a Partner, denoting that it has no access grants available at this time (but should later).
        (WAITLIST, _('Waitlisted')),
    )

    status = models.IntegerField(choices=STATUS_CHOICES,
        default=NOT_AVAILABLE,
        # Translators: In the administrator interface, this text is help text for a field where staff can specify whether this partner should be displayed to users.
        help_text=_('Should this Partner be displayed to users? Is it '
                    'open for applications right now?'))

    renewals_available = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a field where staff specify whether users can request their account be renewed/extended for this partner.
        help_text=_('Can access grants to this partner be renewed? If so, '
            'users will be able to request renewals at any time.'))
            
    accounts_available = models.PositiveSmallIntegerField(blank=True, null=True, 
        # Translators: In the administrator interface, this text is help text for a field where staff specify the total number of available accounts.
        help_text=_('Add number of new accounts to the existing value, not by reseting it to zero.'))
    
    # Optional resource metadata
    # --------------------------------------------------------------------------

    terms_of_use = models.URLField(blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can link to a partner's Terms of Use.
        help_text=_("Link to terms of use. Required if users must agree to "
            "terms of use to get access; optional otherwise."))

    short_description = models.TextField(max_length=1000, blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can provide a description of a partner's available resources.
        help_text=_("Optional short description of this partner's resources."))

    description = models.TextField("long description", blank=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can provide a long description of a partner's available resources.
        help_text=_("Optional detailed description in addition to the short "
        "description such as collections, instructions, notes, special "
        "requirements, alternate access options, unique features, citations notes."))
        
    additional_resources = models.TextField('video tutorials', blank=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can provide additonal help videos (if any) for a partner.
        help_text=_("Comma separated list of video tutorials (URLs)."))
        
    send_instructions = models.TextField(blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can provide instructions to coordinators on sending user data to partners.
        help_text=_("Optional instructions for sending application data to "
            "this partner."))
    
    excerpt_limit = models.PositiveSmallIntegerField(blank=True, null=True,
          # Translators: In the administrator interface, this text is help text for a field where staff can optionally provide a excerpt word limit per article.
          help_text=_("Optional excerpt limit in terms of number of words per article. Leave empty if no limit."))

    excerpt_limit_percentage   = models.PositiveSmallIntegerField(blank=True, null=True, validators = [MaxValueValidator(100)],
          # Translators: In the administrator interface, this text is help text for a field where staff can optionally provide a excerpt word limit per article in terms of percentage per article.
          help_text=_("Optional excerpt limit in terms of percentage (%) of an article. Leave empty if no limit."))
          
    bundle = models.NullBooleanField(
        blank=True, null=True, default=False,
        # Translators: In the administrator interface, this text is help text for a field where staff can specify whether users can access this as part of the Bundle.
        help_text=_("Is this partner a part of the Bundle?"))

    mutually_exclusive = models.NullBooleanField(
        blank=True, null=True,
        default=None,
        # Translators: In the administrator interface, this text is help text for a field where staff can specify whether users can apply for one or multiple collections of resources. Streams means 'collections'.
        help_text=_("If True, users can only apply for one Stream at a time "
        "from this Partner. If False, users can apply for multiple Streams at "
        "a time. This field must be filled in when Partners have multiple "
        "Streams, but may be left blank otherwise."))

    languages = models.ManyToManyField(Language, blank=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can specify the languages a partner has resources in.
        help_text=_("Select all languages in which this partner publishes "
            "content.")
        )

    tags = TaggableManager(through=TaggedTextField, blank=True)

    # This field has to stick around until all servers are using the new tags.
    old_tags = TaggableManager(through=None, blank=True, verbose_name=_('Old Tags'))

    # Non-universal form fields
    # --------------------------------------------------------------------------

    # Some fields are required by all resources for all access grants.
    # Some fields are only required by some resources. This is where we track
    # whether *this* resource requires those optional fields.

    registration_url = models.URLField(blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can link to a partner's registration page.
        help_text=_("Link to registration page. Required if users must sign up "
            "on the partner's website in advance; optional otherwise."))
    real_name = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must specify their real name when applying
        help_text=_('Mark as true if this partner requires applicant names.'))
    country_of_residence = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must specify the country in which they live when applying.
        help_text=_('Mark as true if this partner requires applicant countries '
                    'of residence.'))
    specific_title = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must specify a title for the resource they want to access when applying.
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify the title they want to access.'))
    specific_stream = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must specify a collection of resources when applying.
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify the database they want to access.'))
    occupation = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must specify their occupation when applying.
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify their occupation.'))
    affiliation = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must specify their institutional affiliation (e.g. university) when applying.
        help_text=_('Mark as true if this partner requires applicants to '
                    'specify their institutional affiliation.'))
    agreement_with_terms_of_use = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must agree to Terms of Use when applying.
        help_text=_("Mark as true if this partner requires applicants to agree "
                    "with the partner's terms of use."))
    account_email = models.BooleanField(default=False,
        # Translators: In the administrator interface, this text is help text for a check box where staff can select whether users must first register at the organisation's website before finishing their application.
        help_text=_("Mark as true if this partner requires applicants to have "
                    "already signed up at the partner website."))


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
        if self.account_email and not self.registration_url:
            raise ValidationError('When pre-registration is required, '
                'a link to the registration page must be provided.')


    def get_absolute_url(self):
        return reverse_lazy('partners:detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """Invalidate this partner's pandoc-rendered html from cache"""
        super(Partner, self).save(*args, **kwargs)
        for code in RESOURCE_LANGUAGE_CODES:
          short_description_cache_key = make_template_fragment_key(
              'partner_short_description', [code, self.pk]
          )        
          description_cache_key = make_template_fragment_key(
              'partner_description', [code, self.pk]
          )
          send_instructions_cache_key = make_template_fragment_key(
              'partner_send_instructions', [code, self.pk]
          )
          cache.delete(description_cache_key)
          cache.delete(send_instructions_cache_key)
          cache.delete(short_description_cache_key)

    @property
    def get_languages(self):
        return self.languages.all()


    @property
    def is_waitlisted(self):
        return self.status == self.WAITLIST



class PartnerLogo(models.Model):
    partner = models.OneToOneField('Partner', related_name='logos')
    logo = models.ImageField(blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can upload an image to be used as this partner's logo.
        help_text=_('Optional image file that can be used to represent this '
        'partner.'))



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
        # Translators: In the administrator interface, this text is help text for a field where staff can add the name of a collection of resources. Don't translate Health and Behavioral Sciences.
        help_text=_("Name of stream (e.g. 'Health and Behavioral Sciences). "
            "Will be user-visible and *not translated*. Do not include the "
            "name of the partner here."))
            
    accounts_available = models.PositiveSmallIntegerField(blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff specify the total number of available accounts.
        help_text=_('Add number of new accounts to the existing value, not by reseting it to zero.'))
        
    description = models.TextField(blank=True, null=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can add a description of a collection of resources.
        help_text=_("Optional description of this stream's resources."))

    languages = models.ManyToManyField(Language, blank=True)


    def __unicode__(self):
        # Do not try to also return the partner name here (e.g.
        # "Partnername: Streamname") because that will be hard to
        # internationalize. Returning the atomic stream name gives us more
        # options for how this is displayed in templates.
        return self.name

    def save(self, *args, **kwargs):
        """Invalidate the rendered html stream description from cache"""
        super(Stream, self).save(*args, **kwargs)
        for code in RESOURCE_LANGUAGE_CODES:
          cache_key = make_template_fragment_key('stream_description', [code, self.pk])
          cache.delete(cache_key)

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

    title = models.CharField(max_length=75, blank=True,
        # Translators: In the administrator interface, this text is help text for a field where staff can add someone's job title. Example can be changed to something more language appropriate.
        help_text=_("Organizational role or job title. This is NOT intended "
        "to be used for honorifics. Think 'Director of Editorial Services', "
        "not 'Ms.' Optional."))
    email = models.EmailField()
    full_name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=15,
        # Translators: In the administrator interface, this text is help text for a field where staff can add the 'friendly' version of someone's name. e.g. Sam instead of Samuel. Name can be changed to be language appropriate.
        help_text=_("The form of the contact person's name to use in email "
        "greetings (as in 'Hi Jake')"))


    def __unicode__(self):
        # As with Stream, do not return the partner name here.
        return self.full_name