from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Since we only care about one field we could probably return data in a more
        # sensible format, but this is totally functional.
        fields = ('username',)
