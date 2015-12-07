# README.md

* Set up a postgres database matching the parameters in the DATABASES setting. (Yes, it must be postgres.)
* `pip install -r requirements.txt`
* Set the following environment variables:
    - `DJANGO_DEBUG` (must be `False` on production, can be `True` for testing)
    - `DJANGO_SECRET_KEY`
    - `DJANGO_SETTINGS_MODULE`
* `python manage.py migrate`
* `python manage.py createsuperuser` (follow prompts)

## Configure allauth
In the Django admin site...

1. Add a Site for your domain, matching `settings.SITE_ID` (this will be 1 unless you have overridden it).
2. Add a Social App (socialaccount app) for Wikipedia.
3. Fill in the site and the OAuth app credentials obtained from Wikipedia.

## TODO
Read wmlabs puppetization docs and ensure that you can set this up there. Document accordingly.
