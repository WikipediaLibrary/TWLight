"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
from django import forms
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.generic.edit import FormView

from TWLight.resources.models import Partner

from .forms import BaseApplicationForm, USER_FORM_FIELDS, PARTNER_FORM_OPTIONAL_FIELDS, PARTNER_FORM_BASE_FIELDS
from .models import Application


class RequestForApplicationView(FormView):
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

        """
        --> important <--
        this is now out of sync with your models
        you actually want to persist data to the session (sigh) with partner ids

        then you want to construct Applications as needed in the next view

        and construct your form accordingly
        """
        # Get the IDs of the partner resources they want to apply for.
        # Because we had to prepend some text to the ID in get_form_class,
        # make sure to strip it off here, so we're left with just the ID for
        # ease of database lookups. Store them in the session so we can
        # construct the required form later.
        partner_ids = [int(key[8:]) for key in form.cleaned_data
                       if form.cleaned_data[key]]

        self.request.session['applications_request__partner_ids'] = partner_ids

        return HttpResponseRedirect(reverse('applications:apply'))


        # http://www.slideshare.net/kingkilr/forms-getting-your-moneys-worth
        # multipleformfactory here might be a good way to aggregate



class SubmitApplicationView(FormView):
    template_name = 'applications/apply.html'
    form_class = BaseApplicationForm

    # ~~~~~~~~~~~~~~~~~ Overrides to built-in Django functions ~~~~~~~~~~~~~~~~#

    def dispatch(self, request, *args, **kwargs):
        if not 'applications_request__partner_ids' in request.session.keys():
            messages.add_message(request, messages.WARNING,
                _('You must choose at least one resource you want access to before applying for access.'))
            return HttpResponseRedirect(reverse('applications:request'))

        if len(request.session['applications_request__partner_ids']) == 0:
            messages.add_message(request, messages.WARNING,
                _('You must choose at least one resource you want access to before applying for access.'))
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

        # TODO raw IDs in the admin site

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

            for field in partner_fields:
                label = '{partner}_{field}'.format(partner=partner, field=field)

                try:
                    data = form.cleaned_data[label]
                except KeyError:
                    # Not all forms require all fields, and that's OK.
                    pass

                if data:
                    setattr(app, field, data)

            app.save()
            # TODO test suite should also ensure Application matches our single
            # source of truth

        # And clean up the session so as not to confuse future applications.
        del self.request.session['applications_request__partner_ids']

        return super(SubmitApplicationView, self).form_valid(form)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Local functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def _get_partners(self):
        """
        Get the queryset of Partners with resources the user wants access to.
        These partners were specified in RequestForApplicationView.
        """
        # This key is guaranteed by dispatch() to exist and be nonempty.
        partner_ids = self.request.session['applications_request__partner_ids']
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
        needed_fields = []
        for field in USER_FORM_FIELDS:
            query = {'{field}'.format(field=field): True}
            if partners.filter(**query).count():
                needed_fields.append(field)

        return needed_fields


