from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from TWLight.users.models import Editor, UserProfile

def deactivate(modeladmin, request, queryset):
    for user in queryset:
        if hasattr(user, 'editor'):
            # Delete all optional info on Editor - except homewiki, which we'll
            # keep in order to be able to log them in should they ever
            # reactivate.
            # We can't delete the editor isntance entirely because that would
            # delete associated Applications, which we wish to preserve.
            user.editor.contributions = ''
            user.editor.real_name = ''
            user.editor.country_of_residence = ''
            user.editor.occupation = ''
            user.editor.affiliation = ''
            user.editor.save()

        user.userprofile.terms_of_use = False
        user.userprofile.save()

        user.email = ''
        user.is_active = False
        user.save()


deactivate.short_description = \
    "Deactivate selected accounts"



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



class TWLUserCreationForm(UserCreationForm):
    """
    The default form does not allow usernames to have parentheses, but this
    interacts badly with OAuth-created usernames for WMF staff, as their
    usernames include '(WMF)'.
    """
    username = forms.RegexField(
        label='Username',
        max_length=30,
        regex=r'^[()\w-]+$',
        help_text = _('Required. 30 characters or fewer. Alphanumeric '
                      'characters (letters, digits, hyphens and underscores) '
                      'and parentheses only.'),
        error_message = _('This value must contain only letters, numbers, '
                      'hyphens, underscores, and parentheses.')
        )



class TWLUserChangeForm(UserChangeForm):
    """See TWLUserCreationForm docstring."""
    username = forms.RegexField(
        label='Username',
        max_length=30,
        regex=r'^[()\w-]+$',
        help_text = _('Required. 30 characters or fewer. Alphanumeric '
                      'characters (letters, digits, hyphens and underscores) '
                      'and parentheses only.'),
        error_message = _('This value must contain only letters, numbers, '
                      'hyphens, underscores, and parentheses.')
        )



class UserAdmin(AuthUserAdmin):
    inlines = [EditorInline, UserProfileInline]
    actions = [deactivate]
    list_display = ['username', 'get_wp_username', 'get_wiki', 'is_staff']
    list_filter = ['is_staff', 'is_active', 'is_superuser']
    default_filters = ['is_active__exact=1']
    search_fields = ['editor__wp_username', 'username']
    form = TWLUserChangeForm
    add_form = TWLUserCreationForm

    def get_wp_username(self, user):
        if hasattr(user, 'editor'):
            return user.editor.wp_username
        else:
            return ''
    get_wp_username.short_description = _('Wikipedia username')


    def get_wiki(self, user):
        if hasattr(user, 'editor'):
            return user.editor.home_wiki
        else:
            return ''
    get_wiki.short_description = _('Home wiki')


# Unregister old user admin; register new, improved user admin.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
