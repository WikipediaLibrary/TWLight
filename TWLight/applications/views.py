"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from datetime import date, timedelta
import logging
from reversion import revisions as reversion
from reversion.models import Version


from django import forms
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView

from TWLight.view_mixins import (CoordinatorsOrSelf,
                                 CoordinatorsOnly,
                                 EditorsOnly,
                                 ToURequired)
from TWLight.resources.models import Partner
from TWLight.users.models import Editor

from .helpers import (USER_FORM_FIELDS,
                      PARTNER_FORM_OPTIONAL_FIELDS,
                      PARTNER_FORM_BASE_FIELDS,
                      get_output_for_application)
from .forms import BaseApplicationForm, ApplicationAutocomplete
from .models import Application


logger = logging.getLogger(__name__)

PARTNERS_SESSION_KEY = 'applications_request__partner_ids'


class RequestApplicationView(EditorsOnly, ToURequired, FormView):
    template_name = 'applications/request_for_application.html'

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
            messages.add_message(self.request, messages.INFO,
                _('Please select at least one partner.'))
            return HttpResponseRedirect(reverse('applications:request'))



class _BaseSubmitApplicationView(EditorsOnly, ToURequired, FormView):
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

    def get_form(self, form_class):
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
        Return a list of user-specific data fields required by at least one
        Partner to whom the user is requesting access.
        """
        if not partners:
            return None

        needed_fields = []
        for field in USER_FORM_FIELDS:
            query = {'{field}'.format(field=field): True}
            if partners.filter(**query).count():
                needed_fields.append(field)

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
        fail_msg = _('You must choose at least one resource you want access to before applying for access.')
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
            _('Your application has been submitted. A coordinator will review '
              'it and get back to you. You can check the status of your '
              'applications on this page at any time.'))
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
    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS,
            _('Your application has been submitted. A coordinator will review '
              'it and get back to you. You can check the status of your '
              'applications on your user page page at any time.'))
        user_home = self._get_partners()[0].get_absolute_url()
        return user_home


    def _get_partners(self):
        """
        Get the Partner with resources the user wants access to. There's only
        one (as specified in the URL parameter), but this is called
        _get_partners() and returns a queryset so that
        SubmitSingleApplicationView and SubmitApplicationView have the same
        behavior, and the shared functionality in _BaseSubmitApplicationView
        doesn't have to special-case it.
        """
        partner_id = self.kwargs['pk']
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

        # Set up button group menu.
        context['approved_url'] = reverse_lazy('applications:list_approved')
        context['rejected_url'] = reverse_lazy('applications:list_rejected')
        context['expiring_url'] = reverse_lazy('applications:list_expiring')
        context['pending_url'] = reverse_lazy('applications:list')
        context['sent_url'] = reverse_lazy('applications:list_sent')

        # Add miscellaneous page contents.
        context['include_template'] = \
            'applications/application_list_include.html'

        context['autocomplete_form'] = ApplicationAutocomplete()

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
        except KeyError:
            # Better to ask forgiveness than permission; if the POST data didn't
            # have an editor, the user didn't filter by editor, and that's OK.
            editor = None
        except Editor.DoesNotExist:
            # The format call is guaranteed to work, because if we got here we
            # *don't* have a KeyError.
            logger.exception('Autocomplete requested editor #{pk}, who does '
                'not exist'.format(pk=request.POST['editor']))
            raise

        try:
            partner = Partner.objects.get(pk=request.POST['partner'])
        except KeyError:
            partner = None
        except Partner.DoesNotExist:
            logger.exception('Autocomplete requested partner #{pk}, who does '
                'not exist'.format(pk=request.POST['partner']))
            raise

        filters = [
            # Translators: Editor = wikipedia editor, gender unknown.
            {'label': _('Editor'), 'object': editor},
            {'label': _('Publisher'), 'object': partner}
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
        base_qs = Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION],
                partner__status=Partner.AVAILABLE,
             ).order_by('status', 'partner')

        return base_qs


    def get_context_data(self, **kwargs):
        context = super(ListApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Queue of applications to review')

        context['include_template'] = \
            'applications/application_list_reviewable_include.html'

        # For constructing the dropdown in the batch editing form.
        context['status_choices'] = Application.STATUS_CHOICES

        context['pending_class'] = 'active'

        return context



class ListApprovedApplicationsView(_BaseListApplicationView):

    def get_queryset(self):
        return Application.objects.filter(
                status=Application.APPROVED
             ).order_by('date_closed', 'partner')


    def get_context_data(self, **kwargs):
        context = super(ListApprovedApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Approved applications')

        context['approved_class'] = 'active'

        return context



class ListRejectedApplicationsView(_BaseListApplicationView):

    def get_queryset(self):
        return Application.objects.filter(
                status=Application.NOT_APPROVED
             ).order_by('date_closed', 'partner')


    def get_context_data(self, **kwargs):
        context = super(ListRejectedApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Rejected applications')

        context['rejected_class'] = 'active'

        return context



class ListExpiringApplicationsView(_BaseListApplicationView):
    """
    Lists access grants that are probably about to expire, for Partners who
    are presently Available.
    """

    def get_queryset(self):
        two_months_from_now = date.today() + timedelta(days=60)

        return Application.objects.filter(
                status=Application.APPROVED,
                earliest_expiry_date__lte=two_months_from_now,
                partner__status=Partner.AVAILABLE,
             ).order_by('earliest_expiry_date')


    def get_context_data(self, **kwargs):
        context = super(ListExpiringApplicationsView, self).get_context_data(**kwargs)

        # Translators: these are grants to specific editors whose term limit is about to expire.
        context['title'] = _('Access grants up for renewal')

        # Overrides default. We want different styling for this case to help
        # coordinators prioritize expiring-soon vs. expired-already access
        # grants.
        context['include_template'] = \
            'applications/application_list_expiring_include.html'

        context['expiring_class'] = 'active'

        return context



class ListSentApplicationsView(_BaseListApplicationView):

    def get_queryset(self):
        return Application.objects.filter(
                status=Application.SENT
             ).order_by('date_closed', 'partner')


    def get_context_data(self, **kwargs):
        context = super(ListSentApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Sent applications')

        context['sent_class'] = 'active'

        return context



class EvaluateApplicationView(CoordinatorsOrSelf, ToURequired, UpdateView):
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

    def form_valid(self, form):
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            return super(EvaluateApplicationView, self).form_valid(form)


    def get_context_data(self, **kwargs):
        context = super(EvaluateApplicationView, self).get_context_data(**kwargs)
        context['editor'] = self.object.editor
        context['versions'] = Version.objects.get_for_object(self.object)
        return context


    def get_form(self, form_class):
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
            assert 'applications' in request.POST
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

        for app_pk in request.POST.getlist('applications'):
            try:
                app = Application.objects.get(pk=app_pk)
            except Application.DoesNotExist:
                logger.exception('Could not find app with posted pk {pk}; '
                    'continuing through remaining apps'.format(pk=app_pk))
                continue

            app.status = status
            app.save()

        messages.add_message(request, messages.SUCCESS,
            _('Batch update successful. Thank you for reviewing today.'))

        return HttpResponseRedirect(reverse_lazy('applications:list'))



class ListReadyApplicationsView(CoordinatorsOnly, ListView):
    template_name = 'applications/send.html'

    def get_queryset(self):
        return Partner.objects.filter(
            applications__status=Application.APPROVED).distinct()



class SendReadyApplicationsView(CoordinatorsOnly, DetailView):
    model = Partner
    template_name = 'applications/send_partner.html'

    def get_context_data(self, **kwargs):
        context = super(SendReadyApplicationsView, self).get_context_data(**kwargs)
        apps = self.get_object().applications.filter(
            status=Application.APPROVED)
        app_outputs = {}

        for app in apps:
            app_outputs[app] = get_output_for_application(app)

        context['app_outputs'] = app_outputs

        return context


    def post(self, request, *args, **kwargs):
        apps = self.get_object().applications.filter(
            status=Application.APPROVED)
        for app in apps:
            app.status = Application.SENT
            app.sent_by = request.user
            app.save()

        messages.add_message(self.request, messages.SUCCESS,
            _('All applications have been marked as sent.'))

        return HttpResponseRedirect(reverse(
            'applications:send_partner', kwargs={'pk': self.get_object().pk}))
