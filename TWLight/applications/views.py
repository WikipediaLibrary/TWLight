"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
from django import forms
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseServerError
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from TWLight.resources.models import Partner

from .forms import BaseUserAppForm, BasePartnerAppForm, USER_FORM_FIELDS
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



class SubmitApplicationView(TemplateView):
    template_name = 'applications/apply.html'

    def dispatch(self, request, *args, **kwargs):
        if not 'applications_request__partner_ids' in request.session.keys():
            raise HttpResponseServerError

        if len(request.session['applications_request__partner_ids']) == 0:
            messages.add_message(request, messages.WARNING,
                _('You must choose at least one resource you want access to before applying for access.'))
            return HttpResponseRedirect(reverse('applications:request'))

        return super(SubmitApplicationView, self).dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(SubmitApplicationView, self).get_context_data(**kwargs)
        context['user_form'], context['formset'] = self._get_forms()
        return context


    def _get_partners(self):
        """
        Get the queryset of Partners with resources the user wants access to.
        These partners were specified in RequestForApplicationView.
        """
        # This key is guaranteed by dispatch() to exist and be nonempty.
        partner_ids = self.request.session['applications_request__partner_ids']
        return Partner.objects.filter(id__in=partner_ids)


    def _get_partner_formset(self, partners=None):
        PartnerFormSet = forms.formset_factory(BasePartnerAppForm,
            extra=0)

        if self.request.POST:
            return PartnerFormSet(self.request.POST)
        else:
            return PartnerFormSet(initial=[{'partner': x} for x in partners])


    def _get_user_form(self, partners=None):
        # Set up form to harvest user data. It will only ask for data required
        # by at least one Partner.
        # TODO: single-source-of-truth the USER_FORM_FIELDS via your test suite
        # TODO: use profile data to supply form.initial
        if self.request.POST:
            return BaseUserAppForm(self.request.POST)
        else:
            fields_to_remove = []
            for field in USER_FORM_FIELDS:
                query = {'{field}'.format(field=field): True}
                if not partners.filter(**query).count():
                    fields_to_remove.append(field)

            return BaseUserAppForm(fields_to_remove)


    def _get_forms(self):
        """
        We will dynamically construct a set of forms which harvest exactly the
        information needed for editors to request access to their desired set of
        partner resources.

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

        # create base application form for each partner
        # construct list of forms
        # in the template we will iterate over all of these
        partners = self._get_partners()

        user_form = self._get_user_form(partners)
        partner_forms = self._get_partner_formset(partners)

        # TODO: implement mutually_exclusive Partner behavior
        # TODO: single-source-of-truth the PARTNER_FORM_FIELDS
        # TODO: make sure the forms works when an initial partner isn't supplied,
        # or else is disallowed

        return user_form, partner_forms


    def post(self, request, *args, **kwargs):
        # Write user form things to user data
        # For each Partner, create and save an Application
        partner_forms = self._get_partner_formset()
        user_form = self._get_user_form()

        if partner_forms.is_valid() and user_form.is_valid():
            # do stuff
            pass
        else:
            # do other stuff
            pass

        # Validate forms
        # If invalid, return with errors
        # If valid, then:
        #   update user data
        #   create an Application for each Partner/form
        #   del session key
        #   return to success page; should be user page with translatable message
        pass
