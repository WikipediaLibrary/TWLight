from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.mail import BadHeaderError, send_mail
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic.edit import FormView

from TWLight.emails.forms import ContactUsForm
from TWLight.emails.signals import ContactUs

@method_decorator(login_required, name='post')
class ContactUsView(FormView):
    template_name = 'emails/contact.html'
    form_class = ContactUsForm
    success_url = reverse_lazy('contact')

    def get_initial(self):
        initial = super(ContactUsView, self).get_initial()
        # @TODO: This sort of gets repeated in ContactUsForm.
        # We could probably be factored out to a common place for DRYness.
        if self.request.user.userprofile.use_wp_email:
            initial.update({
                 'email': self.request.user.userprofile.use_wp_email,
            })
        elif ('email' in self.request.GET):
            initial.update({
                 'email': self.request.GET['email'],
            })
        if ('message' in self.request.GET):
            initial.update({
                 'message': self.request.GET['message'],
            })
        initial.update({
            'next': reverse_lazy('contact'),
        })

        return initial

    def form_valid(self, form):
        # Adding an extra check to ensure the user is a wikipedia editor.
        try:
            assert self.request.user.editor
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            ContactUs.new_email.send(
                sender=self.__class__,
                user_email=email
                editor_wp_username=self.request.editor.wp_username
                body=message
            )
            messages.add_message(self.request, messages.SUCCESS,
            # Translators: Shown to users when they successfully add a new partner suggestion.
            _('Your message has been sent. We''ll get back to you soon!'))
            return HttpResponseRedirect(reverse('contact'))
        except (AssertionError, AttributeError) as e:
            messages.add_message (self.request, messages.WARNING,
                # Translators: This message is shown to non-wikipedia editors who attempt to post data to suggestion form.
                _('You must be a Wikipedia editor to do that.'))
            raise PermissionDenied
        return self.request.user.editor