from django.contrib.auth.models import User
from django.db import models

from TWLight.resources.models import Partner


class Application(models.Model):
    class Meta:
        app_label = 'applications'

    # status goes here
    # versioning needs to happen
    user = models.ForeignKey(User)
    partner = models.ForeignKey(Partner)

    rationale = models.TextField(blank=True)
    specific_title = models.CharField(max_length=128, blank=True)
    specific_stream = models.CharField(max_length=128, blank=True)
    comments = models.TextField(blank=True)
    agreement_with_terms_of_use = models.BooleanField(default=False)
