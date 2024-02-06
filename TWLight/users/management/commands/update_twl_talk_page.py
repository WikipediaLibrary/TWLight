from django.core.management.base import BaseCommand
import json
import requests


class Command(BaseCommand):
    help = "Updates a JSON file that contains all the language wikis that have a Wikipedia Library page."

    def handle(self, *args, **options):
        url = "https://en.wikipedia.org/w/rest.php/v1/page/Wikipedia:The_Wikipedia_Library/links/language"
        headers = {"User-Agent": "The Wikipedia Library"}

        response = requests.get(url, headers=headers)
        data = response.json()

        # Adding en wiki because it will not be included in the languages response
        wiki_twl_pages = {
            "en": "https://en.wikipedia.org/wiki/Wikipedia:The_Wikipedia_Library"
        }

        for d in data:
            wiki_twl_pages[d["code"]] = (
                "https://{code}.wikipedia.org/wiki/{title}".format(
                    code=d["code"], title=d["title"]
                )
            )

        with open("locale/language-twl-page.json", "w") as language_file:
            language_file.write(json.dumps(wiki_twl_pages))
