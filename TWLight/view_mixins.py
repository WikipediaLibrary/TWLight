"""
Commonly needed custom view mixins.
"""

from braces.views import UserPassesTestMixin

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy

from TWLight.users.groups import get_coordinators


coordinators = get_coordinators()


class CoordinatorsOrSelf(UserPassesTestMixin):
    """
    Restricts visibility to:
    * Coordinators; or
    * The Editor who owns (or is) the object in the view; or
    * Superusers.

    This mixin assumes that the decorated view has a get_object method, and that
    the object in question has a ForeignKey, 'user', to the User model, or else
    is an instance of User.
    """

    login_url = reverse_lazy('users:test_permission')

    def test_func(self, user):
        try:
            obj = self.get_object()
            if isinstance(obj, User):
                obj_owner_test = (obj == user)
            else:
                obj_owner_test = (self.get_object().user == user)
        except AttributeError:
            obj_owner_test = False

        return (user.is_superuser or
                user in coordinators.user_set.all() or
                obj_owner_test)


class CoordinatorsOnly(UserPassesTestMixin):
    """
    Restricts visibility to:
    * Coordinators; or
    * Superusers.
    """

    login_url = reverse_lazy('users:test_permission')

    def test_func(self, user):
        return (user.is_superuser or
                user in coordinators.user_set.all())


class EditorsOnly(UserPassesTestMixin):
    """
    Restricts visibility to:
    * Editors.

    Unlike other views this does _not_ automatically permit superusers, because
    some views need user.editor to exist, which it may not if the user was
    created via django's createsuperuser command-line function rather than via
    OAuth.
    """

    login_url = reverse_lazy('users:test_permission')

    def test_func(self, user):
        return hasattr(user, 'editor')


class SelfOnly(UserPassesTestMixin):
    """
    Restricts visibility to:
    * The user who owns (or is) the object in question.

    This mixin assumes that the decorated view has a get_object method, and that
    the object in question has a ForeignKey, 'user', to the User model, or else
    is an instance of User.
    """

    login_url = reverse_lazy('users:test_permission')

    def test_func(self, user):
        obj_owner_test = False # set default

        obj = self.get_object()
        if isinstance(obj, User):
            obj_owner_test = (obj == user)
        else:
            obj_owner_test = (self.get_object().user == user)

        return obj_owner_test


class ToURequired(UserPassesTestMixin):
    """
    Restricts visibility to:
    * Users who have agreed with the site's terms of use.
    """

    login_url = reverse_lazy('terms')

    def test_func(self, user):
        return user.userprofile.terms_of_use
