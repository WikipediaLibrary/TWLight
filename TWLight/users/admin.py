# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from TWLight.users.models import Editor, UserProfile, Authorization
from TWLight.users.forms import AuthorizationForm


class EditorInline(admin.StackedInline):
    model = Editor
    max_num = 1
    extra = 1
    can_delete = False
    raw_id_fields = ("user",)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    extra = 1
    can_delete = False
    raw_id_fields = ("user",)
    fieldsets = (
        (
            None,
            {"fields": ("terms_of_use", "terms_of_use_date", "use_wp_email", "lang")},
        ),
        (
            _("Email preferences"),
            {
                "fields": (
                    "send_renewal_notices",
                    "pending_app_reminders",
                    "discussion_app_reminders",
                    "approved_app_reminders",
                )
            },
        ),
    )


class AuthorizationInline(admin.StackedInline):
    form = AuthorizationForm
    model = Authorization
    fk_name = "user"
    extra = 0


class AuthorizationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_partners",
        "stream",
        "get_authorizer_wp_username",
        "get_authorized_user_wp_username",
    )
    search_fields = [
        "partner__company_name",
        "stream__name",
        "authorizer__editor__wp_username",
        "user__editor__wp_username",
    ]

    def get_authorized_user_wp_username(self, authorization):
        if authorization.user:
            user = authorization.user
            if hasattr(user, "editor"):
                return user.editor.wp_username
        else:
            return ""

    get_authorized_user_wp_username.short_description = _("user")

    def get_authorizer_wp_username(self, authorization):
        if authorization.authorizer:
            user = authorization.authorizer
            if hasattr(user, "editor"):
                return user.editor.wp_username
            elif hasattr(user, "username"):
                return user.username
        else:
            return ""

    get_authorizer_wp_username.short_description = _("authorizer")

    def get_partners(self, authorization):
        return "\n".join([p.company_name for p in authorization.partners.all()])


admin.site.register(Authorization, AuthorizationAdmin)


class UserAdmin(AuthUserAdmin):
    inlines = [EditorInline, UserProfileInline, AuthorizationInline]
    list_display = ["username", "get_wp_username", "is_staff"]
    list_filter = ["is_staff", "is_active", "is_superuser"]
    default_filters = ["is_active__exact=1"]
    search_fields = ["editor__wp_username", "username"]

    def get_wp_username(self, user):
        if hasattr(user, "editor"):
            return user.editor.wp_username
        else:
            return ""

    get_wp_username.short_description = _("Username")


# Unregister old user admin; register new, improved user admin.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
