# Sysadmin docs

This documentation is aimed at the system administrator who is setting up an
instance of TWLight. For further details, consult https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/ .

## Translations

See `locale/README.md`.

## Software dependencies

The (versioned) dependencies you will need are indicated in `requirements/`.

For setting this up on Wikimedia Labs, you should install everything in `requirements/base.txt` and `requirements/wmf.txt`. You do not need to install anything in any other settings file.

If using a virtualenv, make sure that the user running the webserver process also has access to the files in that virtualenv! By default they are owned by whichever user installed them, but that is probably not your nginx user.

There are a few dependencies that are not available as python packages, and they have been downloaded directly into the top level of the TWLight app. As of this writing, they are:
* `diff_match_patch`
* `mwoauth`

## Settings
* `settings/production.py` mostly inherits from base.py, but sets a few WMF-specific things. You probably do not need to edit it.
    * An exception: if you have moved the site so that it lives at a different URL, that URL needs to be added to `ALLOWED_HOSTS`. (Other URLs not being used can be safely removed from this list.)
* You *do* need to edit the file `TWLight/settings/production_vars.py` to contain the following:
    * `SECRET_KEY = ` (can be anything, is usually a ~50-character random string; used by Django for security)
    * `CONSUMER_KEY = ` (your Wikimedia OAuth consumer token)
    * `CONSUMER_SECRET = ` (your Wikimedia OAuth secret token)
    * `MYSQL_PASSWORD = ` (the password your MySQL user uses to access the database)

`production_vars.py` is `.gitignore`d, so it will be kept out of version control and you can safely add secret information to it.

## System dependencies

* MySQL server
    * Should have a database named `twlight`
    * And a user named `twlight` with all permissions on `twlight`
        * If you change these names, make sure to update the `DATABASES` variable in `settings/base.py` and `settings/production.py` accordingly
* Web server (nginx)
    * The file `nginx.conf.site` should be copied to `/etc/nginx/sites-available`, and symlinked from `/etc/nginx/sites-enabled`.
    * You are probably done, because `nginx.conf.site` assumes the WMF default `nginx.conf` file is being used. However, if it seems to not be working, copy `nginx.conf.webserver` to `/etc/nginx.nginx.conf`.
    * Make sure an nginx process is running.
* Email
    * TWLight occasionally sends emails. The code is nearly agnostic about its backend, but you do need to set one up.
    * In `settings/local.py` you can see an example of configuring TWLight to use an SMTP server synchronously for mail sending.
        * _Do not do this._ Synchronous mail sending will block the request/response loop and lead to some really long pageload times (and possibly timeouts).
    * `settings/production.py` instead configures djmail to expect a celery backend.
    * TODO make a sample celery config, get it working on heroku
* One-time django commands - you must do these before the first time you run TWLight
    * `python manage.py migrate` (set up database)
    * `python manage.py createinitialrevisions` (see https://django-reversion.readthedocs.io/en/stable/commands.html#createinitialrevisions ; we use this for version history on the Application model)
* Running Django
    * _Do not use `manage.py runserver`_: it is not suitable for production
    * `bin/gunicorn_start.sh` to start the gunicorn process that sits between nginx and Django.
    * The `DJANGO_SETTINGS_MODULE` environment variable must be `TWLight.settings.production`.

## Logs

Application log: `/var/www/html/TWLight/logs/twlight.log`
Gunicorn log: `/var/www/html/TWLight/logs/gunicorn.log`
