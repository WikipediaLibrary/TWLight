"""
Commonly needed custom view mixins.
"""

from braces.views import UserPassesTestMixin

from django.contrib.auth.models import User

from TWLight.users.groups import coordinators

class CoordinatorsOrSelf(UserPassesTestMixin):
    """
    Restricts visibility to:
    * Coordinators; or
    * The Editor who owns (or is) the object in the view; or
    * Superusers.
    """

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

    def test_func(self, user):
        return hasattr(user, 'editor')


class SelfOnly(UserPassesTestMixin):
    """
    Restricts visibility to:
    * The user who owns the object in question.

    This mixin assumes that the decorated view has a get_object method, and that
    the object in question has a ForeignKey, 'user', to the User model.
    """
    def test_func(self, user):
        return (self.get_object().user == user)
