"""
Views for managing applications for resource grants go here.

Examples: users apply for access; coordinators evaluate applications and assign
status.
"""
from django import forms
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView

from TWLight.resources.models import Partner

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
        app = ApplicationContainer()
        app.user = self.request.user

        # We have to save now, not only at our later save() call, because
        # we can't add related objects to a ManyToMany field (in this case,
        # Partners) until the base object has been saved.
        app.save()

        # Get the IDs of the partner resources they want to apply for.
        # Because we had to prepend some text to the ID in get_form_class,
        # make sure to strip it off here, so we're left with just the ID for
        # ease of database lookups.
        partner_ids = [int(key[8:]) for key in form.cleaned_data
                       if form.cleaned_data[key]]

        for partner in Partner.objects.filter(pk__in=partner_ids):
            app.partners.add(partner)

        app.save()

        return HttpResponseRedirect(
            reverse('applications:apply', kwargs={'pk': app.pk})
        )


        # http://www.slideshare.net/kingkilr/forms-getting-your-moneys-worth
        # multipleformfactory here might be a good way to aggregate

class SubmitApplicationView(FormView):

    def get_form_class(self):
        """
        We will dynamically construct a form which harvests exactly the
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
