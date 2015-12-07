from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

class WikipediaAccount(ProviderAccount):
    pass

# TODO possibly relevant https://github.com/mediawiki-utilities/python-mwoauth
# TODO https://www.mediawiki.org/wiki/Extension:OAuth#Using_OAuth
# TODO https://www.mediawiki.org/wiki/OAuth/For_Developers#Python
# TODO on account creation, instantiate Editor and Coordinator classes;
# they need to be inlined in the admin.

"""
Attributes I should get...

username: The MediaWiki username
sub: The MediaWiki user_id
editcount: The user's edit count
confirmed_email: The user has a confirmed email set in MediaWiki
registered: The date when the user registered
groups: A list of groups to which the user belongs
rights: A list of user rights that this user has been granted on the wiki
"""

class WikipediaProvider(OAuth2Provider):
    id = 'wikipedia'
    name = 'Wikipedia'
    package = 'TWLight.wp_allauth'
    account_class = WikipediaAccount

    def get_default_scope(self):
        return ['profile']

    def extract_uid(self, data):
        return str(data['user_id'])

    def extract_common_fields(self, data):
        # Hackish way of splitting the fullname.
        # Asumes no middlenames.
        name = data.get('name', '')
        first_name, last_name = name, ''
        if name and ' ' in name:
            first_name, last_name = name.split(' ', 1)
        return dict(email=data['email'],
                    last_name=last_name,
                    first_name=first_name)

providers.registry.register(WikipediaProvider)
