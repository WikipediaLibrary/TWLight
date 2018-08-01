"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
import bleach
import urllib2
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
import logging
from dal import autocomplete
from reversion import revisions as reversion
from reversion.models import Version
from urlparse import urlparse


from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import IntegerField, Case, When, Count, Q
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView

from TWLight.view_mixins import (CoordinatorOrSelf,
                                 CoordinatorsOnly,
                                 EditorsOnly,
                                 ToURequired,
                                 EmailRequired,
                                 SelfOnly,
                                 DataProcessingRequired,
                                 NotDeleted)
from TWLight.resources.models import Partner
from TWLight.users.groups import get_coordinators
from TWLight.users.models import Editor

from .helpers import (USER_FORM_FIELDS,
                      PARTNER_FORM_OPTIONAL_FIELDS,
                      PARTNER_FORM_BASE_FIELDS,
                      get_output_for_application)
from .forms import BaseApplicationForm, ApplicationAutocomplete
from .models import Application


logger = logging.getLogger(__name__)

personal_data_logger = logging.getLogger('personal_logger')

coordinators = get_coordinators()

PARTNERS_SESSION_KEY = 'applications_request__partner_ids'


class EditorAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Make sure that we aren't leaking info via our form choices.
        if self.request.user.is_superuser:
            editor_qs = Editor.objects.all().order_by('wp_username')
            # Query by wikimedia username
            if self.q:
                editor_qs = editor_qs.filter(wp_username__istartswith=self.q).order_by('wp_username')
        elif coordinators in self.request.user.groups.all():
            editor_qs = Editor.objects.filter(
                     applications__partner__coordinator__pk=self.request.user.pk
                ).order_by('wp_username')
            # Query by wikimedia username
            if self.q:
                editor_qs = editor_qs.filter(wp_username__istartswith=self.q).order_by('wp_username')
        else:
            editor_qs = Editor.objects.none()
        return editor_qs

class PartnerAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Make sure that we aren't leaking info via our form choices.
        if self.request.user.is_superuser:
            partner_qs = Partner.objects.all().order_by('company_name')
            # Query by partner name
            if self.q:
                partner_qs = partner_qs.filter(company_name__istartswith=self.q).order_by('company_name')
        elif coordinators in self.request.user.groups.all():
            partner_qs =  Partner.objects.filter(
                    coordinator__pk=self.request.user.pk
                ).order_by('company_name')
            # Query by partner name
            if self.q:
                partner_qs = partner_qs.filter(company_name__istartswith=self.q).order_by('company_name')
        else:
            partner_qs = Partner.objects.none()
        return partner_qs

class RequestApplicationView(EditorsOnly, ToURequired, EmailRequired, FormView):
    template_name = 'applications/request_for_application.html'

    def get_context_data(self, **kwargs):
        context = super(RequestApplicationView, self).get_context_data(**kwargs)
        context['any_waitlisted'] = Partner.objects.filter(
            status=Partner.WAITLIST).exists()
        return context


    def get_form_class(self):
        """
        Dynamically construct a form which will have a checkbox for every
        partner.
        """
        fields = {}
        field_order = []
        for partner in Partner.objects.all().order_by('company_name'):
            # We cannot just use the partner ID as the field name; Django won't
            # be able to find the resultant data.
            # http://stackoverflow.com/a/8289048
            field_name = 'partner_{id}'.format(id=partner.id)
            fields[field_name] = forms.BooleanField(
                label=partner.company_name,
                required=False,
                # We need to pass the partner to the front end in order to
                # render the partner information tiles. Widget attrs appear to
                # be the place we can stash arbitrary metadata. Ugh.
                widget=forms.CheckboxInput(attrs={'object': partner}))
            field_order.append(partner.company_name)

        form_class = type('RfAForm', (forms.Form,), fields)
        form_class.field_order = field_order
        return form_class


    def form_valid(self, form):
        """
        When users submit a valid request, construct a stub application and
        redirect users to the page where they fill it out.
        """
        # Get the IDs of the partner resources they want to apply for.
        # Because we had to prepend some text to the ID in get_form_class,
        # make sure to strip it off here, so we're left with just the ID for
        # ease of database lookups. Store them in the session so we can
        # construct the required form later.
        partner_ids = [int(key[8:]) for key in form.cleaned_data
                       if form.cleaned_data[key]]

        self.request.session[PARTNERS_SESSION_KEY] = partner_ids

        if len(partner_ids):
            return HttpResponseRedirect(reverse('applications:apply'))
        else:
            messages.add_message(self.request, messages.WARNING,
                #Translators: When a user is on the page where they can select multiple partners to apply to (https://wikipedialibrary.wmflabs.org/applications/request/), they receive this message if they click Apply without selecting anything.
                _('Please select at least one partner.'))
            return HttpResponseRedirect(reverse('applications:request'))



class _BaseSubmitApplicationView(EditorsOnly, ToURequired, EmailRequired, DataProcessingRequired, FormView):
    """
    People can get to application submission in 2 ways:
    1) via RequestApplicationView, which lets people select multiple partners;
    2) via the "apply for access" button on the partner detail page.

    This means there are 2 different ways to tell the SubmitApplicationView
    which partner(s) it is dealing with, but after that point the logic is the
    same. We factor the common logic out here, and use subclasses for the two
    cases.
    """
    template_name = 'applications/apply.html'
    form_class = BaseApplicationForm

    # ~~~~~~~~~~~~~~~~~ Overrides to built-in Django functions ~~~~~~~~~~~~~~~~#

    def get_form(self, form_class=None):
        """
        We will dynamically construct a form which harvests exactly the
        information needed for editors to request access to their desired set of
        partner resources. (Most of the actual work of form construction happens
        in applications/forms.py. This view figures out what data to pass to
        the base form's constructor: which information the partners in this
        application require.)

        In particular:
        * We don't ask for information that we can harvest from their user
          profile.
        * We will ask for optional information if and only if any of the
          requested partners require it.
        * We will ask for optional information once if it is the same for all
          resources (e.g. full name), and once per partner if it differs (e.g.
          specific title requested).

        The goal is to reduce the user's data entry burden to the minimum
        amount necessary for applications to be reviewed.
        """
        if form_class is None:
            form_class = self.form_class

        kwargs = self.get_form_kwargs()

        field_params = {}
        partners = self._get_partners()
        user_fields = self._get_user_fields(partners)

        field_params['user'] = user_fields

        for partner in partners:
            key = 'partner_{id}'.format(id=partner.id)
            fields = self._get_partner_fields(partner)
            field_params[key] = fields

        kwargs['field_params'] = field_params

        return form_class(**kwargs)


    def get_initial(self):
        """
        If we already know the user's real name, etc., use that to prefill form
        fields.
        """
        initial = super(_BaseSubmitApplicationView, self).get_initial()
        editor = self.request.user.editor

        # Our form might not actually have all these fields, but that's OK;
        # unneeded initial data will be discarded.
        for field in USER_FORM_FIELDS:
            initial[field] = getattr(editor, field)

        return initial


    def form_valid(self, form):
        # Add user data to user profile.
        editor = self.request.user.editor
        for field in USER_FORM_FIELDS:
            if field in form.cleaned_data:
                setattr(editor, field, form.cleaned_data[field])

        editor.save()

        # Create an Application for each partner resource. Remember that the
        # partner_id parameters were added as an attribute on the form during
        # form __init__, so we have them available now; no need to re-process
        # them out of our session data. They were also validated during form
        # instantiation; we rely on that validation here.
        partner_fields = PARTNER_FORM_BASE_FIELDS + PARTNER_FORM_OPTIONAL_FIELDS
        for partner in form.field_params:
            partner_id = partner[8:]
            partner_obj = Partner.objects.get(id=partner_id)

            app = Application()
            app.editor = self.request.user.editor
            app.partner = partner_obj
            # Status will be set to PENDING by default.

            for field in partner_fields:
                label = '{partner}_{field}'.format(partner=partner, field=field)

                try:
                    data = form.cleaned_data[label]
                except KeyError:
                    # Not all forms require all fields, and that's OK. However,
                    # we do need to make sure to clear out the value of data
                    # here, or we'll have carried it over from the previous
                    # time through the loop, and who knows what sort of junk
                    # data we'll write into the Application.
                    data = None

                if data == "[deleted]":
                    fail_msg = _('This field consists only of restricted text.')
                    form.add_error(label, fail_msg)
                    return self.form_invalid(form)

                if data:
                    setattr(app, field, data)

            app.save()

        # And clean up the session so as not to confuse future applications.
        del self.request.session[PARTNERS_SESSION_KEY]

        return super(_BaseSubmitApplicationView, self).form_valid(form)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Local functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def _get_partner_fields(self, partner):
        """
        Return a list of the partner-specific data fields required by the given
        Partner.
        """
        return [field for field in PARTNER_FORM_OPTIONAL_FIELDS
                if getattr(partner, field)]


    def _get_user_fields(self, partners=None):
        """
        Return a dict of user-specific data fields required by at least one
        Partner to whom the user is requesting access, with a list of
        partners requesting that data.
        """
        if not partners:
            return None

        needed_fields = {}
        for field in USER_FORM_FIELDS:
            query = {'{field}'.format(field=field): True}
            partners_queried = partners.filter(**query)
            if partners_queried.count():
                requesting_partners = partners_queried.distinct()
                needed_fields[field] = [x.__str__() for x in partners_queried]

        return needed_fields



class SubmitApplicationView(_BaseSubmitApplicationView):
    """
    This is the view used after RequestApplicationView, when one or more
    partners may be in play.
    """

    # ~~~~~~~~~~~~~~~~~ Overrides to built-in Django functions ~~~~~~~~~~~~~~~~#

    def dispatch(self, request, *args, **kwargs):
        """
        Validate inputs.
        """
        # Translators: If a user files an application for a partner but doesn't specify a collection of resources they need, this message is shown.
        fail_msg = _('Choose at least one resource you want access to.')
        if not PARTNERS_SESSION_KEY in request.session.keys():
            messages.add_message(request, messages.WARNING, fail_msg)
            return HttpResponseRedirect(reverse('applications:request'))

        if len(request.session[PARTNERS_SESSION_KEY]) == 0:
            messages.add_message(request, messages.WARNING, fail_msg)
            return HttpResponseRedirect(reverse('applications:request'))

        try:
            partners = self._get_partners()
            if partners.count() == 0:
                messages.add_message(request, messages.WARNING, fail_msg)
                return HttpResponseRedirect(reverse('applications:request'))
        except:
            messages.add_message(request, messages.WARNING, fail_msg)
            return HttpResponseRedirect(reverse('applications:request'))

        return super(SubmitApplicationView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS,
            #Translators: When a user applies for a set of resources, they receive this message if their application was filed successfully.
            _('Your application has been submitted for review. '
              'You can check the status of your applications on this page.'))
        user_home = reverse('users:editor_detail',
            kwargs={'pk': self.request.user.editor.pk})
        return user_home

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Local functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def _get_partners(self):
        """
        Get the queryset of Partners with resources the user wants access to.
        These partners were specified in RequestApplicationView.
        """
        # This key is guaranteed by dispatch() to exist and be nonempty.
        partner_ids = self.request.session[PARTNERS_SESSION_KEY]
        partners = Partner.objects.filter(id__in=partner_ids)
        try:
            assert len(partner_ids) == partners.count()
        except AssertionError:
            logger.exception('Number of partners found does not match number '
                'of IDs provided')
            raise
        return partners



class SubmitSingleApplicationView(_BaseSubmitApplicationView):
    def dispatch(self, request, *args, **kwargs):
        if self._get_partners()[0].status == Partner.WAITLIST:
            #Translators: When a user applies for a set of resources, they receive this message if none are currently available. They are instead placed on a 'waitlist' for later approval.
            messages.add_message(request, messages.WARNING, _("This partner "
                "does not have any access grants available at this time. "
                "You may still apply for access; your application will be "
                "reviewed when access grants become available."))

        return super(SubmitSingleApplicationView, self).dispatch(
            request, *args, **kwargs)


    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS,
            _('Your application has been submitted for review. '
              'You can check the status of your applications on this page.'))
        user_home = self._get_partners()[0].get_absolute_url()
        return user_home


    def _get_partners(self):
        """
        Get the Partner with resources the user wants access to. There's only
        one (as specified in the URL parameter), but this is called
        _get_partners() and returns a queryset so that
        SubmitSingleApplicationView and SubmitApplicationView have the same
        behavior, and the shared functionality in _BaseSubmitApplicationView
        doesn't have to special-case it. Store the partner_id in the session so
        the validator doesn't blow up when we link directly to a partner app..
        """
        partner_id = self.kwargs['pk']

        self.request.session[PARTNERS_SESSION_KEY] = partner_id

        partners = Partner.objects.filter(id=partner_id)
        try:
            assert partners.count() == 1
        except AssertionError:
            logger.exception('Expected 1 partner, got {count}'.format(
                count=partners.count()))
            raise

        return partners



class _BaseListApplicationView(CoordinatorsOnly, ToURequired, ListView):
    """
    Factors out shared functionality for the application list views. Not
    intended to be user-facing. Subclasses should implement get_queryset().
    """
    model = Application

    def _filter_queryset(self, base_qs, editor, partner):
        """
        Handle filters that might have been passed in by post().
        """
        if editor:
            base_qs = base_qs.filter(editor=editor)

        if partner:
            base_qs = base_qs.filter(partner=partner)

        return base_qs


    def _set_object_list(self, filters):
        # If the view lets users apply filters to the queryset, this is where
        # the filtered queryset can be set as the object_list for the view.
        # If the view doesn't have filters, or the user hasn't applied them,
        # this applies default Django behavior.
        base_qs = self.get_queryset()
        if filters:
            editor = filters[0]['object']
            partner = filters[1]['object']
            self.object_list = self._filter_queryset(base_qs=base_qs,
                                                editor=editor,
                                                partner=partner)
        else:
            self.object_list = base_qs


    def get_queryset(self):
        raise NotImplementedError


    def get_context_data(self, **kwargs):
        """
        Subclasses should call super on this and add title, include_template (if
        different from the default), and any other context specific to that
        subclass. If you add pages, be sure to expand the button menu, and tell
        the context which page is currently active.
        """
        # We need to determine self.object_list *before* we do the call to
        # super below, because it will expect self.object_list to be defined.
        # Our object_list varies depending on whether the user has filtered the
        # queryset.
        filters = kwargs.pop('filters', None)

        # If the POST data didn't have an editor, try the GET data.
        # The user might be going through paginated data.
        # There is almost certainly a better way to do this, since we're
        # recreating a data structure from post.
        if not filters:
            try:
                editor_pk = urllib2.unquote(bleach.clean(self.request.GET.get('Editor')))
                if editor_pk:
                    editor = Editor.objects.get(pk=editor_pk)
                else:
                    editor = ''

                partner_pk = urllib2.unquote(bleach.clean(self.request.GET.get('Partner')))
                if partner_pk:
                    partner = Partner.objects.get(pk=partner_pk)
                else:
                    partner = ''

                filters = [
                    # Translators: Editor = wikipedia editor, gender unknown.
                    {'label': _('Editor'), 'object': editor},
                    {'label': _('Partner'), 'object': partner}
                ]
            except:
                logger.info('Unable to set filter from GET data.')
                pass

        self._set_object_list(filters)

        context = super(_BaseListApplicationView, self
            ).get_context_data(**kwargs)

        context['filters'] = filters

        context['object_list'] = self.object_list
        # Set up pagination.
        paginator = Paginator(self.object_list, 20)
        page = self.request.GET.get('page')
        try:
            applications = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            applications = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            applications = paginator.page(paginator.num_pages)

        context['object_list'] = applications

        # Log personal data access
        for app in applications:
            personal_data_logger.info('{user} accessed personal data of '
                '{user2} when listing applications.'.format(
                    user=self.request.user.editor,
                    user2=app.editor))

        # Set up button group menu.
        context['approved_url'] = reverse_lazy('applications:list_approved')
        context['rejected_url'] = reverse_lazy('applications:list_rejected')
        context['renewal_url'] = reverse_lazy('applications:list_renewal')
        context['pending_url'] = reverse_lazy('applications:list')
        context['sent_url'] = reverse_lazy('applications:list_sent')

        # Add miscellaneous page contents.
        context['include_template'] = \
            'applications/application_list_include.html'

        context['autocomplete_form'] = ApplicationAutocomplete(user=self.request.user)

        return context


    def post(self, request, *args, **kwargs):
        """
        Handles filters applied by the autocomplete form, limiting the queryset
        and redisplaying the text. The self.render_to_response() incantation is
        borrowed from django's form_invalid handling.
        """
        try:
            # request.POST['editor'] will be the pk of an Editor instance, if
            # it exists.
            editor = Editor.objects.get(pk=request.POST['editor'])
        except (KeyError, ValueError):
            # The user didn't filter by editor, and that's OK.
            editor = None
        except Editor.DoesNotExist:
            # The format call is guaranteed to work, because if we got here we
            # *don't* have a KeyError.
            logger.exception('Autocomplete requested editor #{pk}, who does '
                'not exist'.format(pk=request.POST['editor']))
            raise

        try:
            partner = Partner.objects.get(pk=request.POST['partner'])
        except (KeyError, ValueError):
            # The user didn't filter by partner, and that's OK.
            partner = None
        except Partner.DoesNotExist:
            logger.exception('Autocomplete requested partner #{pk}, who does '
                'not exist'.format(pk=request.POST['partner']))
            raise

        filters = [
            # Translators: Editor = wikipedia editor, gender unknown.
            {'label': _('Editor'), 'object': editor},
            {'label': _('Partner'), 'object': partner}
        ]

        return self.render_to_response(self.get_context_data(filters=filters))



class ListApplicationsView(_BaseListApplicationView):

    def get_queryset(self, **kwargs):
        """
        List only the open applications from available partners: that makes this
        page useful as a reviewer queue. Approved and rejected applications
        should be listed elsewhere: kept around for historical reasons, but kept
        off the main page to preserve utility (and limit load time).
        """
        if self.request.user.is_superuser:
            base_qs = Application.objects.filter(
                    status__in=[Application.PENDING, Application.QUESTION],
                    partner__status__in=[Partner.AVAILABLE, Partner.WAITLIST],
                    editor__isnull=False
                ).exclude(editor__user__groups__name='restricted').order_by(
                    'status', 'partner', 'date_created')

        else:
            base_qs = Application.objects.filter(
                    status__in=[Application.PENDING, Application.QUESTION],
                    partner__status__in=[Partner.AVAILABLE, Partner.WAITLIST],
                    partner__coordinator__pk=self.request.user.pk,
                    editor__isnull=False
                ).exclude(editor__user__groups__name='restricted').order_by(
                    'status', 'partner', 'date_created')

        return base_qs


    def get_context_data(self, **kwargs):
        context = super(ListApplicationsView, self).get_context_data(**kwargs)
        #Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Pending' applications.
        context['title'] = _('Applications to review')

        context['include_template'] = \
            'applications/application_list_reviewable_include.html'

        # For constructing the dropdown in the batch editing form.
        context['status_choices'] = Application.STATUS_CHOICES

        context['pending_class'] = 'active'

        return context



class ListApprovedApplicationsView(_BaseListApplicationView):

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.objects.filter(
                    status=Application.APPROVED,
                    editor__isnull=False
                ).exclude(editor__user__groups__name='restricted').order_by(
                    'status', 'partner', 'date_created')
        else:
            return Application.objects.filter(
                    status=Application.APPROVED,
                    partner__coordinator__pk=self.request.user.pk,
                    editor__isnull=False
                ).exclude(editor__user__groups__name='restricted').order_by(
                    'status', 'partner', 'date_created')

    def get_context_data(self, **kwargs):
        context = super(ListApprovedApplicationsView, self).get_context_data(**kwargs)
        #Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Approved' applications.
        context['title'] = _('Approved applications')

        context['approved_class'] = 'active'

        return context



class ListRejectedApplicationsView(_BaseListApplicationView):

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.objects.filter(
                    status=Application.NOT_APPROVED,
                    editor__isnull=False
                ).order_by('date_closed', 'partner')
        else:
            return Application.objects.filter(
                    status=Application.NOT_APPROVED,
                    partner__coordinator__pk=self.request.user.pk,
                    editor__isnull=False
                ).order_by('date_closed', 'partner')

    def get_context_data(self, **kwargs):
        context = super(ListRejectedApplicationsView, self).get_context_data(**kwargs)
        #Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Rejected' applications.
        context['title'] = _('Rejected applications')

        context['rejected_class'] = 'active'

        return context



class ListRenewalApplicationsView(_BaseListApplicationView):
    """
    Lists access grants that users have requested, but not received, renewals
    for.
    """

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.objects.filter(
                     status__in=[Application.PENDING, Application.QUESTION],
                     parent__isnull=False,
                     editor__isnull=False
                ).order_by('-date_created')
        else:
            return Application.objects.filter(
                     status__in=[Application.PENDING, Application.QUESTION],
                     partner__coordinator__pk=self.request.user.pk,
                     parent__isnull=False,
                     editor__isnull=False
                ).order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super(ListRenewalApplicationsView, self).get_context_data(**kwargs)

        # Translators: #Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Up for renewal' applications.
        context['title'] = _('Access grants up for renewal')

        context['renewal_class'] = 'active'

        return context



class ListSentApplicationsView(_BaseListApplicationView):

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Application.objects.filter(
                    status=Application.SENT,
                    editor__isnull=False
                ).order_by('date_closed', 'partner')
        else:
            return Application.objects.filter(
                    status=Application.SENT,
                    partner__coordinator__pk=self.request.user.pk,
                    editor__isnull=False
                ).order_by('date_closed', 'partner')

    def get_context_data(self, **kwargs):
        context = super(ListSentApplicationsView, self).get_context_data(**kwargs)
        #Translators: On the page listing applications, this is the page title if the coordinator has selected the list of 'Sent' applications.
        context['title'] = _('Sent applications')

        context['sent_class'] = 'active'

        return context



class EvaluateApplicationView(NotDeleted, CoordinatorOrSelf, ToURequired, UpdateView):
    """
    Allows Coordinators to:
    * view single applications
    * view associated editor metadata
    * assign status
    """
    model = Application
    fields = ['status']
    template_name_suffix = '_evaluation'
    success_url = reverse_lazy('applications:list')

    def dispatch(self, request, *args, **kwargs):
        application = self.get_object()

        # Log personal data access
        personal_data_logger.info('{user} accessed personal data of '
            '{user2} in application {app_pk}.'.format(
                user=request.user.editor,
                user2=application.editor,
                app_pk=application.pk))

        return super(EvaluateApplicationView, self).dispatch(
            request, *args, **kwargs)

    def form_valid(self, form):
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            return super(EvaluateApplicationView, self).form_valid(form)


    def get_context_data(self, **kwargs):
        context = super(EvaluateApplicationView, self).get_context_data(**kwargs)
        context['editor'] = self.object.editor
        context['versions'] = Version.objects.get_for_object(self.object)
        return context


    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.form_class
        form = super(EvaluateApplicationView, self).get_form(form_class)

        form.helper = FormHelper()
        form.helper.add_input(Submit(
            'submit',
            # Translators: this lets a reviewer set the status of a single application.
            _('Set application status'),
            css_class='center-block'))

        return form



class BatchEditView(CoordinatorsOnly, ToURequired, View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            assert 'batch_status' in request.POST

            status = request.POST['batch_status']
            assert int(status) in [Application.PENDING,
                                   Application.QUESTION,
                                   Application.APPROVED,
                                   Application.NOT_APPROVED,
                                   Application.SENT]
        except (AssertionError, ValueError):
            # ValueError will be raised if the status cannot be cast to int.
            logger.exception('Did not find valid data for batch editing')
            return HttpResponseBadRequest()

        try:
            assert 'applications' in request.POST
        except AssertionError:
            messages.add_message(self.request, messages.WARNING,
                #Translators: When a coordinator is batch editing (https://wikipedialibrary.wmflabs.org/applications/list/), they receive this message if they click Set Status without selecting any applications.
                _('Please select at least one application.'))
            return HttpResponseRedirect(reverse('applications:list'))

        # IMPORTANT! It would be tempting to just do QuerySet.update() here,
        # but that does NOT send the pre_save signal, which is doing some
        # important work for Applications. This includes handling the closing
        # dates for applications and sending email notifications to editors
        # about their applications.
        for app_pk in request.POST.getlist('applications'):
            try:
                app = Application.objects.get(pk=app_pk)
            except Application.DoesNotExist:
                logger.exception('Could not find app with posted pk {pk}; '
                    'continuing through remaining apps'.format(pk=app_pk))
                continue

            app.status = status
            app.save()
        #Translators: After a coordinator has changed the status of a number of applications, this message appears.
        messages.add_message(request, messages.SUCCESS,
            _('Batch update successful.'))

        return HttpResponseRedirect(reverse_lazy('applications:list'))



class ListReadyApplicationsView(CoordinatorsOnly, ListView):
    template_name = 'applications/send.html'

    def get_queryset(self):
        # Find all approved applications, then list the relevant partners.
        # Don't include applications from restricted users when generating
        # this list.
        base_queryset = Application.objects.filter(
                            status=Application.APPROVED,
                            editor__isnull=False
                            ).exclude(
                                editor__user__groups__name='restricted')

        partner_list = Partner.objects.filter(
            applications__in=base_queryset).distinct()

        # Superusers can see all unrestricted applications, otherwise
        # limit to ones from the current coordinator
        if self.request.user.is_superuser:
            return partner_list
        else:
            return partner_list.filter(
                    coordinator__pk=self.request.user.pk
                )


class SendReadyApplicationsView(CoordinatorsOnly, DetailView):
    model = Partner
    template_name = 'applications/send_partner.html'

    def get_context_data(self, **kwargs):
        context = super(SendReadyApplicationsView, self).get_context_data(**kwargs)
        apps = self.get_object().applications.filter(
            status=Application.APPROVED, editor__isnull=False).exclude(
                editor__user__groups__name='restricted'
                )
        app_outputs = {}

        for app in apps:
            app_outputs[app] = get_output_for_application(app)

            # Log personal data access
            personal_data_logger.info('{user} accessed personal data of '
                '{user2} when sending data for partner '
                '{partner_name}.'.format(
                    user=self.request.user.editor,
                    user2=app.editor,
                    partner_name=self.get_object()))

        context['app_outputs'] = app_outputs

        return context


    def post(self, request, *args, **kwargs):
        try:
            request.POST['applications']
        except KeyError:
            logger.exception('Posted data is missing required parameter')
            return HttpResponseBadRequest()

        # Use getlist, don't just access the POST dictionary value using
        # the 'applications' key! If you just access the dict element you will
        # end up treating it as a string - thus if the pk of 80 has been
        # submitted, you will end up filtering for pks in [8, 0] and nothing
        # will be as you expect. getlist will give you back a list of items
        # instead of a string, and then you can use it as desired.
        app_pks = request.POST.getlist('applications')

        try:
            self.get_object().applications.filter(pk__in=app_pks).update(
                status=Application.SENT, sent_by=request.user)
        except ValueError:
            # This will be raised if something that isn't a number gets posted
            # as an app pk.
            logger.exception('Invalid value posted')
            return HttpResponseBadRequest()
        #Translators: After a coordinator has marked a number of applications as 'sent', this message appears.
        messages.add_message(self.request, messages.SUCCESS,
            _('All selected applications have been marked as sent.'))

        return HttpResponseRedirect(reverse(
            'applications:send_partner', kwargs={'pk': self.get_object().pk}))



class RenewApplicationView(SelfOnly, DataProcessingRequired, View):
    """
    This view takes an existing Application and creates a clone, with new
    dates and a FK back to the original application.
    """

    def get_object(self):
        app = Application.objects.get(pk=self.kwargs['pk'])

        try:
            assert (app.status == Application.APPROVED) or (app.status == Application.SENT)
        except AssertionError:
            logger.exception('Attempt to renew unapproved app #{pk} has been '
                'denied'.format(pk=app.pk))
            messages.add_message(self.request, messages.WARNING, 'Attempt to renew '
                'unapproved app #{pk} has been denied'.format(pk=app.pk))
            raise PermissionDenied

        return app


    def get(self, request, *args, **kwargs):
        # Figure out where users should be returned to.
        return_url = reverse('users:home') # set default

        try:
            referer = request.META['HTTP_REFERER']
            if referer:
                domain = urlparse(referer).netloc

                if domain in settings.ALLOWED_HOSTS:
                    return_url = referer
        except KeyError:
            # If we don't have an HTTP_REFERER, using the default is fine.
            pass

        # Attempt renewal.
        app = self.get_object()
        
        renewal = app.renew()

        if not renewal:
            messages.add_message(request, messages.WARNING, _('This object '
                'cannot be renewed. (This probably means that you have already '
                'requested that it be renewed.)'))
            return HttpResponseRedirect(return_url)

        # Translators: If a user requests the renewal of their account, this message is shown to them.
        messages.add_message(request, messages.INFO, _('Your renewal request '
            'has been received. A coordinator will review your request.'))
        return HttpResponseRedirect(return_url)
