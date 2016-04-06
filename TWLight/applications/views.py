"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django import forms
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic.list import ListView
from django.views.generic.edit import FormView, UpdateView

from TWLight.resources.models import Partner, Stream

from .helpers import (USER_FORM_FIELDS,
                      PARTNER_FORM_OPTIONAL_FIELDS,
                      PARTNER_FORM_BASE_FIELDS)
from .forms import BaseApplicationForm
from .models import Application


PARTNERS_SESSION_KEY = 'applications_request__partner_ids'


class RequestApplicationView(FormView):
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
                label=partner.company_name, required=False)
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

        return HttpResponseRedirect(reverse('applications:apply'))


        # http://www.slideshare.net/kingkilr/forms-getting-your-moneys-worth
        # multipleformfactory here might be a good way to aggregate



class SubmitApplicationView(FormView):
    template_name = 'applications/apply.html'
    form_class = BaseApplicationForm

    # ~~~~~~~~~~~~~~~~~ Overrides to built-in Django functions ~~~~~~~~~~~~~~~~#

    def dispatch(self, request, *args, **kwargs):
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
        initial = super(SubmitApplicationView, self).get_initial()
        editor = self.request.user.editor

        # Our form might not actually have all these fields, but that's OK;
        # unneeded initial data will be discarded.
        for field in USER_FORM_FIELDS:
            initial[field] = getattr(editor, field)

        return initial


    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS,
            _('Your application has been submitted. A coordinator will review '
              'it and get back to you. You can check the status of your '
              'applications on this page at any time.'))
        user_home = reverse('users:editor_detail',
            kwargs={'pk': self.request.user.pk})
        return user_home


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
            app.user = self.request.user
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
                    if field == 'specific_stream':
                        stream = Stream.objects.get(pk=data)
                        setattr(app, field, stream)
                    else:
                        setattr(app, field, data)

            app.save()
            # TODO test suite should also ensure Application matches our single
            # source of truth

        # And clean up the session so as not to confuse future applications.
        del self.request.session[PARTNERS_SESSION_KEY]

        return super(SubmitApplicationView, self).form_valid(form)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Local functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def _get_partners(self):
        """
        Get the queryset of Partners with resources the user wants access to.
        These partners were specified in RequestForApplicationView.
        """
        # This key is guaranteed by dispatch() to exist and be nonempty.
        partner_ids = self.request.session[PARTNERS_SESSION_KEY]
        return Partner.objects.filter(id__in=partner_ids)


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



class ListApplicationsView(ListView):
    model = Application

    def get_queryset(self):
        """
        List only the open applications: that makes this page useful as a
        reviewer queue. Approved and rejected applications should be listed
        elsewhere: kept around for historical reasons, but kept off the main
        page to preserve utility (and limit load time).
        """
        return Application.objects.filter(
                status__in=[Application.PENDING, Application.QUESTION]
             ).order_by('status', 'partner')


    def get_context_data(self, **kwargs):
        context = super(ListApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Queue of applications to review')

        approved_url = reverse_lazy('applications:list_approved')
        rejected_url = reverse_lazy('applications:list_rejected')
        context['intro_text'] = _("""
          This page lists only applications that still need to be reviewed.
          You may also consult <a href="{approved_url}">approved</a> and
          <a href="{rejected_url}">rejected</a> applications. 
        """).format(approved_url=approved_url, rejected_url=rejected_url)

        return context



class ListApprovedApplicationsView(ListView):
    model = Application

    def get_queryset(self):
        return Application.objects.filter(
                status=Application.APPROVED
             ).order_by('user', 'partner')


    def get_context_data(self, **kwargs):
        context = super(ListApprovedApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Approved applications')

        open_url = reverse_lazy('applications:list')
        rejected_url = reverse_lazy('applications:list_rejected')
        context['intro_text'] = _("""
          This page lists only applications that have been approved.
          You may also consult <a href="{open_url}">pending or
          under-discussion</a> and <a href="{rejected_url}">rejected</a>
          applications. 
        """).format(open_url=open_url, rejected_url=rejected_url)

        return context

    # TODO: paginate



class ListRejectedApplicationsView(ListView):
    model = Application

    def get_queryset(self):
        return Application.objects.filter(
                status=Application.NOT_APPROVED
             ).order_by('user', 'partner')


    def get_context_data(self, **kwargs):
        context = super(ListRejectedApplicationsView, self).get_context_data(**kwargs)

        context['title'] = _('Rejected applications')

        open_url = reverse_lazy('applications:list')
        approved_url = reverse_lazy('applications:list_approved')
        context['intro_text'] = _("""
          This page lists only applications have been rejected.
          You may also consult <a href="{open_url}">pending or
          under-discussion</a> and <a href="{approved_url}">approved</a>
          applications. 
        """).format(open_url=open_url, approved_url=approved_url)

        return context

    # TODO: paginate



class EvaluateApplicationView(UpdateView):
    """
    Allows Coordinators to:
    * view applications
    * view associated editor metadata
    * assign status

    TODO: let them add questions/comments and figure out how to communicate those
    TODO: access control to just Coordinators
    TODO: internationalize form labels
    """
    model = Application
    fields = ['status']
    template_name_suffix = '_evaluation_form'
    success_url = reverse_lazy('applications:list')


    def get_context_data(self, **kwargs):
        context = super(EvaluateApplicationView, self).get_context_data(**kwargs)
        context['editor'] = self.object.user.editor
        return context

    def get_form(self, form_class):
        form = super(EvaluateApplicationView, self).get_form(form_class)

        form.helper = FormHelper()
        form.helper.add_input(Submit(
            'submit',
            _('Set application status'),
            css_class='center-block'))

        return form

# Application evaluation workflow needs...
# ~~listview: all open applications.~~ filterable by user, status - check milestones/desiderata
# ~~evaluation view: app details, user details, status-setting form~~
# add reversion - how should it be displayed? do I want to track who made changes?
# ~~add status field - what are the options?~~
# ~~add section to user page where they can see application statuses~~
# ~~Remove coordinator class,~~ add coordinator group, add access limits
# do I want any kind of locking on application evaluation, so two people don't
# review/edit the same app at once? or assignment?
# Comments - check the scope, and then if at all possible attach comments to
# app reviews so that whichever reviewer is on it can see the history. and
# notify people that they have comments (either via email or via wikimedia edit API on the talk page).
# Be really transparent about who can see which page.
# make sure people cannot set status on their own apps, even if they are coordinators
# make sure people CAN see/comment on their apps
