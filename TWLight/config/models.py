# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings

def get_community_page_url(language):
    """
    Given a language code, returns a community page if one exists,
    otherwise returns None.
    """
    try:
        community_page = CommunityPage.objects.get(lang=language)
        return community_page.url
    except CommunityPage.DoesNotExist:
        return None


class CommunityPage(models.Model):
    class Meta:
        verbose_name = "Community page"
        verbose_name_plural = "Community pages"

    url = models.URLField(
        help_text="Full URL for a local community page."
    )

    lang = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        choices=settings.LANGUAGES,
        help_text="Language",
        unique=True,
    )
