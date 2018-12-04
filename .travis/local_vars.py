MYSQL_PASSWORD='twlight'
SECRET_KEY='twlight'
TWLIGHT_OAUTH_PROVIDER_URL='https://meta.wikimedia.org/w/index.php'
TWLIGHT_OAUTH_CONSUMER_KEY='null'
TWLIGHT_OAUTH_CONSUMER_SECRET='null'
ALLOWED_HOSTS = ['localhost']
REQUEST_BASE_URL = 'http://localhost/'
# Ugh. Have to set debug to false to get the storage engine to return URLS with hashes.
# Travis was returning some interesting errors when this was not happening.
# https://docs.djangoproject.com/en/1.11/ref/contrib/staticfiles/#manifeststaticfilesstorage
DEBUG = False
