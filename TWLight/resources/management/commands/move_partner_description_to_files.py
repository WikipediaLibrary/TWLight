import json
import logging
import os
import pypandoc

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str

from TWLight.resources.models import Partner

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creates files for translatable partner descriptions"

    def handle(self, *args, **options):
        twlight_home = settings.TWLIGHT_HOME
        locale_dir = "{twlight_home}/locale".format(twlight_home=twlight_home)

        # Using listdir for directory traversal instead of os.walk because
        # we only need to traverse the first level of the locale/ directory
        for dir in os.listdir(locale_dir):
            language_dir = os.path.join(locale_dir, dir)
            # Check if the element within local/ directory is also a directory
            # A directory here represents a language in the application
            if os.path.isdir(language_dir):
                partner_dict = {}
                partners = Partner.objects.all()
                for partner in partners:
                    partner_description_key = "{name}_description".format(
                        name=partner.pk
                    )
                    partner_short_description_key = "{name}_short_description".format(
                        name=partner.pk
                    )

                    description_field_name = "description_{lang}".format(lang=dir)
                    short_description_field_name = "short_description_{lang}".format(
                        lang=dir
                    )

                    description_value = self._get_partner_descriptions(
                        partner, description_field_name
                    )

                    short_description_value = self._get_partner_descriptions(
                        partner, short_description_field_name
                    )

                    partner_dict[partner_description_key] = description_value
                    partner_dict[
                        partner_short_description_key
                    ] = short_description_value

                    self._create_json_file(language_dir, partner_dict)

    def _get_partner_descriptions(self, partner, field_name):
        try:
            field_object = partner._meta.get_field(field_name)
            field_value = field_object.value_from_object(partner)
        except FieldDoesNotExist:
            return ""

        if field_value is None or field_value == "":
            return ""

        return pypandoc.convert_text(field_value, "html", format="mediawiki")

    def _create_json_file(self, language_dir, partner_dict):
        file_name = "{language_dir}/partner_descriptions.json".format(
            language_dir=language_dir
        )
        with open(file_name, "w", encoding="utf-8") as partner_descriptions_file:
            json.dump(partner_dict, partner_descriptions_file, indent=4)
            partner_descriptions_file.write("\n")
