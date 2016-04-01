from django.contrib.auth.models import User
from django.db import models

from TWLight.resources.models import Partner


class Application(models.Model):
    class Meta:
        app_label = 'applications'

    PENDING = 0
    QUESTION = 1
    APPROVED = 2
    NOT_APPROVED = 3

    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (QUESTION, 'Question'),
        (APPROVED, 'Approved'),
        (NOT_APPROVED, 'Not approved'),
    )

    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)

    user = models.ForeignKey(User)
    partner = models.ForeignKey(Partner)

    rationale = models.TextField(blank=True)
    specific_title = models.CharField(max_length=128, blank=True)
    specific_stream = models.CharField(max_length=128, blank=True)
    comments = models.TextField(blank=True)
    agreement_with_terms_of_use = models.BooleanField(default=False)
