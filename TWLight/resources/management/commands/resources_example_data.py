from faker import Faker
import random
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from TWLight.resources.factories import SuggestionFactory, VideoFactory
from TWLight.resources.models import Language, Partner, AccessCode

class Command(BaseCommand):
    help = "Modifies the partners already loaded in the database with a few extra features."

    def handle(self, *args, **options):
        all_partners = Partner.even_not_available.all()
        tag_list = ["science", "humanities", "social science", "history",
                    "law", "video", "multidisciplinary"]
        fake = Faker()

        coordinators = User.objects.filter(groups__name='coordinators')

        # Set coordinators for all partners since fixtures don't help the cause
        for _ in all_partners:
            if _.coordinator is None:
                _.coordinator = random.choice(coordinators)
                _.save()
        
        
        for partner in all_partners:
            for tag in random.sample(tag_list, random.randint(1,4)):
                partner.tags.add(tag)
                partner.save()

        
        # Set 15 partners to have somewhere between 1 and 5 video tutorial URLs
        for partner in random.sample(all_partners, 15):
            for _ in range(random.randint(1, 5)):
                VideoFactory(
                    partner = partner,
                    tutorial_video_url = fake.url()
                    )
                    
        
        # Generate a few number of suggestions with upvotes
        all_users = User.objects.exclude(is_superuser=True)
        author_user = random.choice(all_users)
        for _ in range(random.randint(3, 10)):
            suggestion = SuggestionFactory(
                  description = fake.paragraph(nb_sentences=10),
                  author = author_user
                  )
            suggestion.save()
            suggestion.upvoted_users.add(author_user)
            random_users = random.sample(all_users, random.randint(1, 10))
            suggestion.upvoted_users.add(*random_users)


        # Get all partners with access codes as their authorisation method
        # and generate their random access codes.
        access_code_partners = Partner.objects.filter(authorization_method = Partner.CODES)
        
        for partner in access_code_partners:
            for i in range(25):
                new_access_code = AccessCode()
                new_access_code.code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
                new_access_code.partner = partner
                new_access_code.save()
