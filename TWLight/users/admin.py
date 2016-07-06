from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.models import User

from TWLight.users.models import Editor, UserProfile

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



class UserAdmin(AuthUserAdmin):
    inlines = [EditorInline, UserProfileInline]



# Unregister old user admin; register new, inlined user admin.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
