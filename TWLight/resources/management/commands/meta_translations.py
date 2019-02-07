import ast
import logging
import requests
from bs4 import BeautifulSoup

from django.conf import settings
from django.core.management.base import BaseCommand

from TWLight.resources.models import Partner

class Command(BaseCommand):
    help = 'Grabs short and long description translations from Meta and inserts them into the database'
    
    def handle(self, *args, **kwargs):
        all_partners = Partner.even_not_available.all()
        languages_on_file = settings.LANGUAGES

        languages_on_revision_field = {}
        for each_partner in all_partners:
            if each_partner.short_description_last_revision_ids is not None:
                languages_on_revision_field = ast.literal_eval(each_partner.short_description_last_revision_ids)
            for every_language in languages_on_file:
                if every_language[0] not in languages_on_revision_field:
                    languages_on_revision_field[every_language[0]] = None
            each_partner.short_description_last_revision_ids = languages_on_revision_field

            response = requests.get('https://meta.wikimedia.org/w/api.php?action=query&format=json&meta=messagegroupstats&mgsgroup=page-Library_Card_platform%2FTranslation%2FPartners%2FShort_description%2F{partner_pk}'.format(partner_pk=each_partner.id))
            language_data = response.json()
            if 'error' in language_data:
                print 'No short_description for partner {}.'.format(each_partner)
            else:
                messagegroupstats = language_data.get('query').get('messagegroupstats')
                
                for every_messagegroupstat in messagegroupstats:
                    if every_messagegroupstat.get('translated') > 0 and every_messagegroupstat.get('code') in languages_on_revision_field:
                      print every_messagegroupstat.get('code')
                      response = requests.get('https://meta.wikimedia.org/w/api.php?action=parse&format=json&page=Library_Card_platform%2FTranslation%2FPartners%2FShort_description%2F{partner_pk}/{language_code}&prop=wikitext|revid'.format(partner_pk=each_partner.id, language_code=every_messagegroupstat.get('code')))
                      short_desc_json = response.json()
                      if 'error' in short_desc_json:
                          print 'No short_description for partner {}.'.format(each_partner)
                      else:
                          revision_id = int(short_desc_json.get('parse').get('revid'))
                          last_revision_id = languages_on_revision_field.get(every_messagegroupstat.get('code'))
                          
                          if last_revision_id is None or int(last_revision_id) != revision_id:
                              languages_on_revision_field[every_messagegroupstat.get('code')] = revision_id
                              short_desc_html = short_desc_json.get('parse').get('wikitext').get('*')
                              unicode_short_desc = BeautifulSoup(short_desc_html, 'lxml')
                              short_desc = unicode_short_desc.find('div').get_text()
                              language_code = every_messagegroupstat.get('code').replace('-', '_')
                              short_description_language_type = 'short_description_' + language_code
                              # remove
                              print short_desc
                              print 'Last revision id is {0}. New revision id is {1}'.format(last_revision_id, revision_id)
                              setattr(each_partner, short_description_language_type, short_desc)
                              each_partner.save()
                          # remove
                          else:
                              print 'no changes have been made'

