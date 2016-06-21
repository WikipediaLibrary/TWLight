# Sysadmin docs

This documentation is aimed at the system administrator who is setting up an
instance of TWLight. For further details, consult https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/ .

## Translations

See `locale/README.md`.

## Software dependencies

The (versioned) dependencies you will need are indicated in `requirements/`.

For setting this up on Wikimedia Labs, you should install everything in `requirements/base.txt` and `requirements/mwf.txt`. You do not need to install anything in any other settings file.

There are a few dependencies that are not available as debian packages, and they have been downloaded directly into the top level of the TWLight app. As of this writing, they are:
* `diff_match_patch`
* `durationfield` (This can be removed, modulo updating its import statements, should TWLight be upgraded to Django 1.8, which includes durationfield natively.)
* `mwoauth`
* `djmail`

## System dependencies

* mysql server
    * should have a database named `twlight`
    * create a user with permissions to `twlight`
* web server
    * it should be configured to serve static files from `TWLight/collectedstatic`
    * otherwise it should let Django handle URL routing
    * Here is an example nginx.conf file that successfully serves Django: https://github.com/MeasureTheFuture/mothership_beta/blob/master/config/nginx.conf
* `settings/production.py`
    * Set `DATABASES['default']['USER']` and `DATABASES['default']['PASSWORD']` to match your mysql user
    * Set `ALLOWED_HOSTS` to match your webserver
    * Change the `SECRET_KEY` if desired (can be anything, should be kept secret)
    * Set `CONSUMER_KEY` and `CONSUMER_SECRET` to whatever you need to authenticate to Wikimedia OAuth
    * Mostly this file just inherits from the base settings file, and that's fine.
* email
    * TWLight occasionally sends emails. The code is nearly agnostic about its backend, but you do need to set one up.
    * In `settings/local.py` you can see an example of configuring TWLight to use an SMTP server synchronously for mail sending.
        * _Do not do this._ Synchronous mail sending will block the request/response loop and lead to some really long pageload times (and possibly timeouts).
    * `settings/production.py` instead configures djmail to expect a celery backend.
    * TODO make a sample celery config, get it working on heroku
* running Django
    * _Do not use `manage.py runserver`_: it is not suitable for production
    * `gunicorn` is often used to run Django; for a working example, see https://github.com/MeasureTheFuture/mothership_beta/blob/master/bin/gunicorn_start
    * `DJANGO_SETTINGS_MODULE` must be `TWLight.settings.production`
