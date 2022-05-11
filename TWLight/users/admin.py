# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session

from TWLight.users.models import (
    Editor,
    EditorLog,
    UserProfile,
    Authorization,
    get_company_name,
)
from TWLight.users.forms import AuthorizationAdminForm, AuthorizationInlineForm


class EditorInline(admin.StackedInline):
    model = Editor
    max_num = 1
    extra = 1
    can_delete = False
    raw_id_fields = ("user",)
    readonly_fields = (
        "wp_editcount",
        "wp_editcount_updated",
    )


class EditorLogInline(admin.StackedInline):
    model = EditorLog
    can_delete = False
    raw_id_fields = ("editor",)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    max_num = 1
    extra = 1
    can_delete = False
    raw_id_fields = ("user",)
    readonly_fields = ("my_library_cache_key",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "terms_of_use",
                    "terms_of_use_date",
                    "use_wp_email",
                    "lang",
                    "my_library_cache_key",
                )
            },
        ),
        (
            "Email preferences",
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


class AuthorizationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_partners_company_name",
        "get_authorizer_wp_username",
        "get_authorized_user_wp_username",
    )
    search_fields = [
        "partners__company_name",
        "authorizer__editor__wp_username",
        "user__editor__wp_username",
    ]

    form = AuthorizationAdminForm

    def get_authorized_user_wp_username(self, authorization):
        if authorization.user:
            user = authorization.user
            if hasattr(user, "editor"):
                return user.editor.wp_username
        else:
            return ""

    get_authorized_user_wp_username.short_description = "user"

    def get_authorizer_wp_username(self, authorization):
        if authorization.authorizer:
            user = authorization.authorizer
            if hasattr(user, "editor"):
                return user.editor.wp_username
            elif hasattr(user, "username"):
                return user.username
        else:
            return ""

    get_authorizer_wp_username.short_description = "authorizer"

    def get_partners_company_name(self, authorization):
        return get_company_name(authorization)

    get_partners_company_name.short_description = "partners"


admin.site.register(Authorization, AuthorizationAdmin)


class AuthorizationInline(admin.StackedInline):
    form = AuthorizationAdminForm
    model = Authorization
    fk_name = "user"
    extra = 0


class UserAdmin(AuthUserAdmin):
    inlines = [EditorInline, UserProfileInline, AuthorizationInline]
    list_display = ["username", "get_wp_username", "email", "is_staff"]
    list_filter = ["is_staff", "is_active", "is_superuser"]
    default_filters = ["is_active__exact=1"]
    search_fields = ["editor__wp_username", "username", "email"]

    def get_wp_username(self, user):
        if hasattr(user, "editor"):
            return user.editor.wp_username
        else:
            return ""

    get_wp_username.short_description = "Username"


class EditorLogAdmin(admin.ModelAdmin):
    model = EditorLog
    list_display = (
        "editor",
        "timestamp",
        "editcount",
    )
    search_fields = [
        "editor__wp_username",
    ]


admin.site.register(EditorLog, EditorLogAdmin)

# Unregister old user admin; register new, improved user admin.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Cribbed from: https://stackoverflow.com/a/4978234
class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()

    list_display = ["session_key", "_session_data", "expire_date"]


admin.site.register(Session, SessionAdmin)
