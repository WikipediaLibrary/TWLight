# -*- coding: utf-8 -*-

from django.contrib import admin, messages
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



class AuthorizationInline(admin.StackedInline):
    form = AuthorizationForm
    model = Authorization
    fk_name="authorized_user"
    extra = 0



class AuthorizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'partner', 'stream', 'get_authorizer_wp_username', 'get_authorized_user_wp_username')

    def get_authorized_user_wp_username(self, authorization):
        if authorization.authorized_user:
            user = authorization.authorized_user
            if hasattr(user, 'editor'):
                return user.editor.wp_username
        else:
            return ''

    get_authorized_user_wp_username.short_description = _('authorized_user')

    def get_authorizer_wp_username(self, authorization):
        if authorization.authorizer:
            user =  authorization.authorizer
            if hasattr(user, 'editor'):
                return user.editor.wp_username
        else:
            return ''

    get_authorizer_wp_username.short_description = _('authorizer')



class UserAdmin(AuthUserAdmin):
    inlines = [EditorInline, UserProfileInline, AuthorizationInline]
    list_display = ['username', 'get_wp_username', 'is_staff']
    list_filter = ['is_staff', 'is_active', 'is_superuser']
    default_filters = ['is_active__exact=1']
    search_fields = ['editor__wp_username', 'username']

    def get_wp_username(self, user):
        if hasattr(user, 'editor'):
            return user.editor.wp_username
        else:
            return ''
    get_wp_username.short_description = _('Username')


# Unregister old user admin; register new, improved user admin.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)