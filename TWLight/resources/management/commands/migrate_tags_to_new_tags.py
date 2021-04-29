from django.core.management.base import BaseCommand

from TWLight.resources.models import Partner


class Command(BaseCommand):
    help = "Migrates content from the tags column to the new_tags column"

    def handle(self, *args, **options):
        partners = Partner.objects.all()

        for partner in partners:
            new_tags_dict = {}
            tag_names = []
            tags = partner.tags.all()
            for tag in tags:
                if tag.name == "sciences" or tag.name == "social":
                    tag_name = "social-sciences_tag"
                else:
                    tag_name = "{tag_name}_tag".format(tag_name=tag.name)

                if tag_name not in tag_names:
                    tag_names.append(tag_name)

            new_tags_dict["tags"] = tag_names

            partner.new_tags = new_tags_dict

            partner.save()
