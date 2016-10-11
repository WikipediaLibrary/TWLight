# Sysadmin docs

This documentation is aimed at the system administrator who is setting up an
instance of TWLight. For further details, consult https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/ .

When full paths are not given, the files are in the project root (`/var/www/html/TWLight/`).

## System dependencies

This assumes you are running on Debian (Jessie).

### Mail
* `sudo apt-get install mailutils`
* `sudo apt-get install postfix`
    * When it asks, set twl-test.wmflabs.org as FQDN

This should just work with the default settings.

More about Django and mail:
    * TWLight occasionally sends emails. The code is nearly agnostic about its backend, but you do need to set one up.
    * In `settings/local.py` you can see an example of configuring TWLight to use an SMTP server synchronously for mail sending.
        * _Do not do this in production._ Synchronous mail sending will block the request/response loop and lead to some really long pageload times (and possibly timeouts).
    * `settings/production.py` instead configures djmail to expect postfix.
    * This will be unsustainable if the system finds itself sending a lot of email; you will want to set up a celery task queue allowing mail to be sent asynchronously, and set the djmail backend accordingly.

### OAuth
* Get credentials as a wikimedia OAuth consumer.
* Fill in `CONSUMER_SECRET` and `CONSUMER_KEY` in `TWLight/settings/production_vars.py` accordingly
    * This file is `.gitignore`d and should thus be kept out of version control; you can safely add secrets to it.

### virtualenv
* Install virtualenv.
    * You'll need to also `sudo apt-get install libmysqlclient-dev python-dev build-essential` for virtualenv to work.
    * If you see an error, `unable to execute 'x86_64-linux-gnu-gcc': No such file or directory`, you don't have `python-dev` and/or `build-essential`.
* You can now install django dependencies via `pip install -r requirements/wmf.txt`.

### nginx
* `sudo apt-get install nginx`
* Copy `nginx.conf.site` to `/etc/nginx/sites-available` and then symlink it  from `/etc/nginx/sites-enabled`.
* Grant the nginx user permissions on `/var/www/html/TWLight`.
* `systemctl start nginx.service` (or `systemctl reload nginx.service` if it was already running)
* Now you are probably done, because `nginx.conf.site` assumes the WMF default `nginx.conf` file is being used. However, if it seems to not be working, copy `nginx.conf.webserver` to `/etc/nginx.nginx.conf`.

### MySQL server
Install and run a MySQL (or MariaDB) server.

* Create a database named `twlight`
* Create a user named `twlight` with all permissions on `twlight`
    * If you change these names, make sure to update the `DATABASES` variable in `settings/base.py` and `settings/production.py` accordingly


## Software dependencies

The (versioned) dependencies you will need are indicated in `requirements/`.

For setting this up on Wikimedia Labs, you should `pip install -r requirements/wmf.txt`. You do not need to install anything in any other requirements file.

If using a virtualenv, make sure that the user running the webserver process also has access to the files in that virtualenv! By default they are owned by whichever user installed them, but that is probably not your nginx user.

## Running Django

### Settings
* `settings/production.py` mostly inherits from base.py, but sets a few WMF-specific things. You probably do not need to edit it.
    * An exception: if you have moved the site so that it lives at a different URL, that URL needs to be added to `ALLOWED_HOSTS`. (Other URLs not being used can be safely removed from this list.)
* You *do* need to edit the file `TWLight/settings/production_vars.py` to contain the following:
    * `SECRET_KEY = ` (can be anything, is usually a ~50-character random string; used by Django for security)
    * `CONSUMER_KEY = ` (your Wikimedia OAuth consumer token)
    * `CONSUMER_SECRET = ` (your Wikimedia OAuth secret token)
    * `MYSQL_PASSWORD = ` (the password your MySQL user uses to access the database)

`production_vars.py` is `.gitignore`d, so it will be kept out of version control and you can safely add secret information to it.

### One-time setup commands
You must do these before the first time you run TWLight.

* `python manage.py migrate` (set up database)
* `python manage.py createinitialrevisions` (see https://django-reversion.readthedocs.io/en/stable/commands.html#createinitialrevisions ; we use this for version history on the Application model)

### Starting your Django server
* _Do not use `manage.py runserver`_: it is not suitable for production
* `bin/gunicorn_start.sh` to start the gunicorn process that sits between nginx and Django.
* The `DJANGO_SETTINGS_MODULE` environment variable, if set, must be `TWLight.settings.production`.
    * It's fine not to set this variable; there is a sensible default.

### Deploying updated code
* `cd /var/www/html/TWLight`
* git pull your updates
* `python manage.py migrate`
    * This is only required if there are database schema changes to apply, but will not hurt if there aren't.
* `python manage.py collectstatic`
    * This is only required if there are stylesheet changes to apply, but will not hurt if there aren't.
* Kill and restart gunicorn

## Logs

Application log: `/var/www/html/TWLight/logs/twlight.log`
Gunicorn log: `/var/www/html/TWLight/logs/gunicorn.log`

Postfix and nginx log to their system defaults.

## Translations
The TWLight alpha ships with English and French. If you have translation files in a new language to deploy (yay!), or updates to an existing language file,
see `locale/README.md`.
