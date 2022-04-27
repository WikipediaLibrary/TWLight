from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from TWLight.users.models import UserProfile


class FavoriteCollectionSerializer(serializers.Serializer):
    partner_pk = serializers.IntegerField(source="partner.pk")
    added = serializers.BooleanField(required=False)
    user_profile_pk = serializers.IntegerField(source="userprofile.pk")

    def save(self):
        """
        add or remove partner from favorites
        """
        partner_pk = self.validated_data.get("partner").get("pk")
        added = None
        user_profile = get_object_or_404(
            UserProfile, pk=self.validated_data.get("userprofile").get("pk")
        )

        favorites = user_profile.favorites.all()
        favorite_pks = [f.pk for f in favorites]
        if partner_pk in favorite_pks:
            # partner is already in favorites, unfavoriting this partner
            user_profile.favorites.remove(partner_pk)
            self.validated_data.update({"added": False})
        else:
            user_profile.favorites.add(partner_pk)
            self.validated_data.update({"added": True})
        # Updating favorites invalidates the my_library cache
        user_profile.delete_my_library_cache()

        return self.validated_data


class UserSerializer(serializers.ModelSerializer):
    wp_username = serializers.CharField(source="editor.wp_username")

    class Meta:
        model = User
        # Since we only care about one field we could probably return data in a more
        # sensible format, but this is totally functional.
        fields = ("wp_username",)
