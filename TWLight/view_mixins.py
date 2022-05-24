"""
Commonly needed custom view mixins.

Note that these do *not* use something like django-braces' UserPassesTestMixin,
because we may need to use multiple tests in one view (e.g. must be a
coordinator AND must have agreed to the terms of use). If we used that mixin,
test functions and login URLs would overwrite each other. Using the dispatch
function and super() means we can chain as many access tests as we'd like.
"""
from itertools import chain
from urllib.parse import urlencode
from urllib.parse import ParseResult

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, Http404

from TWLight.applications.models import Application
from TWLight.resources.models import Partner
from TWLight.users.models import Editor
from TWLight.users.helpers.editor_data import editor_bundle_eligible
from TWLight.users.groups import COORDINATOR_GROUP_NAME, RESTRICTED_GROUP_NAME

import logging

logger = logging.getLogger(__name__)


class BaseObj(object):
    """
    Normalizes the objects to reduce repetitive try/except blocks for this attribute.
    """

    def get_object(self):
        try:
            return super(BaseObj, self).get_object()
        except AttributeError:
            return None


def test_func_coordinators_only(user):
    obj_coordinator_test = user.is_superuser  # Skip subsequent test if superuser.
    if not obj_coordinator_test:
        obj_coordinator_test = user.groups.filter(name=COORDINATOR_GROUP_NAME).exists()
    return obj_coordinator_test


class CoordinatorsOnly(object):
    """
    Restricts visibility to:
    * Superusers; or
    * Coordinators.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_coordinators_only(request.user):
            messages.add_message(
                request, messages.WARNING, "You must be a coordinator to do that."
            )
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class StaffOnly(object):
    """
    Restricts visibility to:
    * Staff.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.add_message(
                request, messages.WARNING, "You must be staff to do that."
            )
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


def test_func_partner_coordinator(obj, user):
    obj_partner_coordinator_test = (
        user.is_superuser
    )  # Skip subsequent test if superuser.
    if not obj_partner_coordinator_test:
        # If the user is a coordinator run more tests
        if obj and user.groups.filter(name=COORDINATOR_GROUP_NAME).exists():
            # Return true if the object is an editor and has
            # at least one application to a partner for whom
            # the user is a designated coordinator.
            if isinstance(obj, Editor):
                obj_partner_coordinator_test = Application.objects.filter(
                    editor__pk=obj.pk, partner__coordinator__pk=user.pk
                ).exists()
            # Return true if the object is an application to a
            # partner for whom the user is a designated coordinator
            elif isinstance(obj, Application):
                # When coordinators view their own application
                # Return none if the partner has no coordinator
                if obj.partner.coordinator is None:
                    return None
                obj_partner_coordinator_test = obj.partner.coordinator.pk == user.pk
            # Return true if the object is a partner for whom the user is a designated coordinator
            elif isinstance(obj, Partner):
                obj_partner_coordinator_test = obj.coordinator.pk == user.pk

    return obj_partner_coordinator_test


class PartnerCoordinatorOnly(BaseObj):
    """
    Restricts visibility to:
    * Superusers; or
    * The designated Coordinator for partner related to the object.

    This mixin assumes that the decorated view has a get_object method, and that
    the object in question has a ForeignKey, 'user', to the User model, or else
    is an instance of User.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_partner_coordinator(self.get_object(), request.user):
            messages.add_message(
                request,
                messages.WARNING,
                "You must be the designated coordinator or the owner to do that.",
            )
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


def test_func_self_only(obj, user):
    obj_owner_test = False  # set default

    try:
        if isinstance(obj, User):
            obj_owner_test = obj.pk == user.pk
        else:
            obj_owner_test = obj.user.pk == user.pk
    except AttributeError:
        pass

    return obj_owner_test


class SelfOnly(BaseObj):
    """
    Restricts visibility to:
    * The user who owns (or is) the object in question.

    This mixin assumes that the decorated view has a get_object method, and that
    the object in question has a ForeignKey, 'user', to the User model, or else
    is an instance of User.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_self_only(self.get_object(), request.user):
            messages.add_message(
                request, messages.WARNING, "You must be the owner to do that."
            )
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


def test_func_partner_coordinator_or_self(obj, user):
    return test_func_partner_coordinator(obj, user) or test_func_self_only(obj, user)


class PartnerCoordinatorOrSelf(BaseObj):
    """
    Restricts visibility to:
    * Superusers; or
    * The designated Coordinator for partner related to the object; or
    * The Editor who owns (or is) the object in the view.

    This mixin assumes that the decorated view has a get_object method, and that
    the object in question has a ForeignKey, 'user', to the User model, or else
    is an instance of User.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_partner_coordinator_or_self(self.get_object(), request.user):
            messages.add_message(
                request,
                messages.WARNING,
                "You must be the designated coordinator or the owner to do that.",
            )
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


def test_func_editors_only(user):
    return hasattr(user, "editor")


class EditorsOnly(object):
    """
    Restricts visibility to:
    * Editors.

    Unlike other views this does _not_ automatically permit superusers, because
    some views need user.editor to exist, which it may not if the user was
    created via django's createsuperuser command-line function rather than via
    OAuth.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_editors_only(request.user):
            messages.add_message(
                request,
                messages.WARNING,
                "You must be a coordinator or an editor to do that.",
            )
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class EligibleEditorsOnly(object):
    """
    Restricts visibility to:
    * Eligible Editors.

    Raises Permission denied for non-editors.
    Redirects to my_library with message for ineligible editors.
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not test_func_editors_only(user):
            messages.add_message(
                request,
                messages.WARNING,
                "You must be a coordinator or an editor to do that.",
            )
            raise PermissionDenied
        elif not editor_bundle_eligible(user.editor):
            # Send ineligible editors to my_library for info on eligibility.
            return HttpResponseRedirect(reverse_lazy("users:my_library"))
        return super().dispatch(request, *args, **kwargs)


def test_func_tou_required(user):
    try:
        return user.is_superuser or user.userprofile.terms_of_use
    except AttributeError:
        # AnonymousUser won't have a userprofile...but AnonymousUser hasn't
        # agreed to the Terms, either, so we can safely deny them.
        return False


class ToURequired(object):
    """
    Restricts visibility to:
    * Users who have agreed with the site's terms of use.
    * Superusers.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_tou_required(request.user):
            messages.add_message(
                request,
                messages.INFO,
                "You need to agree to the terms of use before you can do that.",
            )

            # Remember where they were trying to go, so we can redirect them
            # back after they agree. There's logic in TermsView to pick up on
            # this parameter.
            next_path = request.path
            next_param = urlencode({REDIRECT_FIELD_NAME: next_path})
            path = reverse_lazy("terms")
            new_url = ParseResult(
                scheme="",
                netloc="",
                path=str(path),
                params="",
                query=str(next_param),
                fragment="",
            ).geturl()
            return HttpResponseRedirect(new_url)

        return super().dispatch(request, *args, **kwargs)


def test_func_email_required(user):
    return bool(user.email) or user.is_superuser


class EmailRequired(object):
    """
    Restricts visibility to:
    * Users who have an email on file.
    * Superusers.
    """

    def dispatch(self, request, *args, **kwargs):
        if not test_func_email_required(request.user):
            messages.add_message(
                request,
                messages.INFO,
                "You need to have an email address on file before you can do that.",
            )

            # Remember where they were trying to go, so we can redirect them
            # back after they agree. There's logic in TermsView to pick up on
            # this parameter.
            next_path = request.path
            next_param = urlencode({REDIRECT_FIELD_NAME: next_path})
            path = reverse_lazy("users:email_change")
            new_url = ParseResult(
                scheme="",
                netloc="",
                path=str(path),
                params="",
                query=str(next_param),
                fragment="",
            ).geturl()
            return HttpResponseRedirect(new_url)

        return super().dispatch(request, *args, **kwargs)


def test_func_data_processing_required(user):
    return user.groups.filter(name=RESTRICTED_GROUP_NAME).exists()


class DataProcessingRequired(object):
    """
    Used to restrict views from users with data processing restricted.
    """

    def dispatch(self, request, *args, **kwargs):
        if test_func_data_processing_required(request.user):
            # No need to give the user a message because they will already
            # have the generic data processing notice.
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


def test_func_not_deleted(user):
    return user.editor is None


class NotDeleted(BaseObj):
    """
    Used to check that the submitting user hasn't deleted their account.
    Without this, users hit a Server Error if trying to navigate directly
    to an app from a deleted user.
    """

    def dispatch(self, request, *args, **kwargs):
        if test_func_not_deleted(self.get_object()):
            raise Http404

        return super().dispatch(request, *args, **kwargs)


class DedupMessageMixin(object):
    """
    Used by custom session storage to prevent storing duplicate messages.
    cribbed directly from: https://stackoverflow.com/a/25157660
    """

    def add(self, level, message, extra_tags):
        messages = chain(self._loaded_messages, self._queued_messages)
        for m in messages:
            if m.message == message:
                return
        return super().add(level, message, extra_tags)
