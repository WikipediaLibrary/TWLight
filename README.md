# README.md

You might need to sudo or otherwise alter permissions to be able to execute these commands.

TODO whoops python3

## Server setup
### Prepare basics
* `apt-get update`
* `apt-get install python-pip`
* `apt-get install python-dev` (TODO: or python3-dev)
* `apt-get install -y build-essential`
* `apt-get install libpq-dev`

### Install app
We'll do most of the app configuration later, but we need to pull this in first so we have its `nginx.conf` file available for setting up nginx.

* `mkdir /www-data`
* `git clone https://github.com/thatandromeda/TWLight.git`

### nginx
* `apt-get install nginx`
* `cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig`
* `cp /www-data/TWLight/nginx.conf /etc/nginx/`
* `useradd www`
* `mkdir /www-data/logs`
* `chown -R www /www-data/`

### postgres
You must use postgres; TWLight is not compatible with other database backends.

* `apt-get install postgresql postgresql-contrib`
* `sudo -- sudo -u postgres psql postgres` (Yes, you need `sudo` twice and the double underscore. See https://wikitech.wikimedia.org/wiki/Help:Sudo_Policies .)
* `\password postgres` (Keep track of this password.)
* `create database twlight;`
* `\q`
* Set an environment variable, `DJANGO_POSTGRES_PASSWORD`, equal to the postgres database password you created earlier.

### Django dependencies
* `cd /www-data/TWLight`
* `mkdir TWLight/logs`
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
