import datetime

from django_comments.forms import CommentForm
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_text
from django.conf import settings


class CommentWithoutEmail(CommentForm):
    def get_comment_create_data(self, **kwargs):
        # Override the default comment form behaviour, with two left out fields
        # From Stack Overflow https://stackoverflow.com/questions/1456267/django-comments-want-to-remove-user-url-not-expand-the-model-how-to/4766543#4766543
        return dict(
            content_type=ContentType.objects.get_for_model(self.target_object),
            object_pk=force_text(self.target_object._get_pk_val()),
            user_name=self.cleaned_data["name"],
            comment=self.cleaned_data["comment"],
            submit_date=datetime.datetime.now(),
            site_id=settings.SITE_ID,
            is_public=True,
            is_removed=False,
        )


CommentWithoutEmail.base_fields.pop("url")
CommentWithoutEmail.base_fields.pop("email")
