from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models

from TWLight.resources.models import Partner


class Application(models.Model):
    # status goes here
    # versioning needs to happen
    user = models.ForeignKey(User)
    partners = models.ForeignKey(Partner)

    rationale = models.TextField(blank=True)
    title_requested = models.CharField(max_length=128, blank=True)
    stream_requested = models.CharField(max_length=128, blank=True)
    comments = models.TextField(blank=True)
    agreement_with_terms = models.BooleanField(default=False)
