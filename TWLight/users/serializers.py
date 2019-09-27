from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    wp_username = serializers.CharField(source='editor.wp_username')

    class Meta:
        model = User
        # Since we only care about one field we could probably return data in a more
        # sensible format, but this is totally functional.
        fields = ('wp_username',)
