# Sysadmin docs

This documentation is aimed at the system administrator who is setting up an
instance of TWLight. For further details, consult https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/ .

When full paths are not given, the files are in the project root (`/var/www/html/TWLight/`).

## To create a new server
### These steps take place outside of your server
* Create a new instance (see https://wikitech.wikimedia.org/wiki/Help:Instances#Add_Instance_link) within the twl project. Its instance details should match those of the existing instance.
    * These instructions expect Debian (Jessie). If the existing instance is something else, these instructions should be tested and updated.
* Set up a web proxy for your instance: https://wikitech.wikimedia.org/wiki/Help:Proxy
    * Use port 443 for your proxy.
    * You shouldn't need to do the security management steps as twl should already have port 443 open on the default security group.
* Get a Wikimedia OAuth consumer key and secret.

### ssh into your server to do these steps
* Confirm that you have the following installed on your instance: Python 2.7, /etc/exim4/, git.
* Create the web user and group
    * `sudo adduser www`
    * Generate a password; leave the rest blank
    * `sudo addgroup twlight`
    * `sudo adduser www twlight`
* Install system dependencies
    * `sudo apt-get install libmysqlclient-dev python-dev build-essential python-pip nginx mariadb-server`
    * Create and record a root password for the MariaDB server. 
    * (Note that the MySQL server should automatically be started as a result of this installation; if it's not, you'll need to bring it up manually.)
* Install the codebase
    * `cd /var/www/html/`
    * `sudo git clone https://github.com/thatandromeda/TWLight.git`
* Configure nginx
    * `sudo cp /var/www/html/TWLight/nginx.conf.site /etc/nginx/sites-available/twlight`
    * `sudo ln -s /etc/nginx/sites-available/twlight /etc/nginx/sites-enabled/twlight`
    * Change the `server_name` in `/etc/nginx/sites-available/twlight` to your server URL.
    * `sudo systemctl start nginx.service`
* Install and set up virtualenv
    * `sudo pip install virtualenv` (note: relies on pip, installed in earlier step)
    * `cd /home/www/`
    * `sudo virtualenv TWLight`
* Install Django dependencies into virtualenv
    * `source /home/www/TWLight/bin/activate`
    * `sudo pip install -r /var/www/html/TWLight/requirements/wmf.txt`
* Set up database
    * Load time zones:
        * `mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root mysql -p` 
        * Enter the database root password you created earlier when prompted
    * Create database and user:
        * `mysql -u root -p`
        * Enter the database root password you created earlier when prompted
        * `CREATE DATABASE twlight CHARACTER SET = 'utf8';`
        * Create and record a password for your database user (which you will use in the next step).
        * `GRANT ALL PRIVILEGES on twlight.* to twlight@'localhost' IDENTIFIED BY '<password>';`
        * `\q`
* Set local variables
    * `sudo touch /var/www/html/TWLight/TWLight/settings/production_vars.py`
    * Add the following lines to `production_vars.py`:
        * `MYSQL_PASSWORD='<your MySQL user (not root) password>'`
        * `SECRET_KEY='<your Django secret key>'` (Your secret key can be anything, but is generally a 50-character string of letters, numbers, and special characters.)
        * `CONSUMER_KEY='<your wikimedia oauth consumer key>'`
        * `CONSUMER_SECRET='<your wikimedia oauth consumer secret>'`
        * (Note: This file is `.gitignore`d and should therefore be kept out of version control; you can safely add secrets to it.)
    * Edit the list of `ALLOWED_HOSTS` in `/var/www/html/TWLight/TWLight/settings/production.py` (*not* `production_vars.py`) to match your server's URL(s).
* Rectify permissions
    * `touch /var/www/html/TWLight/TWLight/logs/twlight.log`
    * `touch /var/www/html/TWLight/TWLight/logs/gunicorn.log`
    * `sudo chown -vR www /home/www/TWLight`
    * `sudo chown -vR :twlight /var/www/html/TWLight`
    * `sudo chmod -vR g+w /var/www/html/TWLight`
    * `sudo chmod -vR g+w /var/www/html/TWLight/TWLight/logs/*`
    * `sudo chmod -vR g+w /var/www/html/TWLight/TWLight/collectedstatic/`
* Do one-time Django setup steps
    * `cd /var/www/html/TWLight`
    * `sudo python manage.py syncdb`
        * Do set up a superuser - otherwise you won't be able to log into the admin.
    * `sudo python manage.py migrate`
    * `sudo python manage.py createinitialrevisions` (see https://django-reversion.readthedocs.io/en/stable/commands.html#createinitialrevisions)
    * `sudo python manage.py collectstatic`
    * Through the web interface, at `/admin`, make sure that your default Site URL matches your server URL.
* Run Django
    * `sudo bin/gunicorn_start.sh`
        * This should probably be run as www, not root, but it crashes; not sure where the permissions problem is.
    * _Do not use `python manage.py runserver`_: it is not suitable for production
    * You don't need to set the `DJANGO_SETTINGS_MODULE` environment variable; it defaults to `TWLight.settings.production`.
        * Don't change this unless you know things about deploying Django in production.


**TODO**
oauth....or maybe NOT oauth, as we should disallow account creation outside admin
update gunicorn_start.sh to use a virtualenv in /home/www, and alter production to use permissions properly
    except I have to figure out how to allow www to start gunicorn first
edit the rest of this doc
decide what must be checked before you promote code to production

## To deploy updated code
Once updates have been git pushed from their local development environment to the repo, ssh into the server and...
* `cd /var/www/html/TWLight`
* `sudo git pull origin master`
* `su - www`; enter your password for user www; `source /home/www/TWLight/bin/activate`; `pip install -r /var/www/html/TWLight/requirements/wmf.txt`; `exit`
    * This is only required if there are dependency changes to install, but will not hurt if there aren't.
* `sudo python manage.py migrate`
    * This is only required if there are database schema changes to apply, but will not hurt if there aren't.
* `sudo python manage.py collectstatic`
    * This is only required if there are stylesheet changes to apply, but will not hurt if there aren't.
* Kill and restart gunicorn: `ps -ef | grep gunicorn`, `sudo kill [process id]`, `sudo bin/gunicorn_start &`

## Background info & troubleshooting

### After Wikimedia server trouble
* Check permissions on everything (including the virtualenv) - they may not be what you expect.
* Make sure gunicorn is running (it does not yet come back automatically after a reboot).

### Mail
* TWLight occasionally sends emails. The code is nearly agnostic about its backend, but you do need to set one up.
* It's currently configured for synchronous email sending.
* This will be unsustainable if the system finds itself sending a lot of email; you will want to set up a celery task queue allowing mail to be sent asynchronously, and set the djmail backend in `TWLight/settings/production.py` accordingly.

### virtualenv
* You'll need `libmysqlclient-dev python-dev build-essential` for virtualenv to work (they are all installed by an apt-get near the beginning of the instructions).
* If you see an error, `unable to execute 'x86_64-linux-gnu-gcc': No such file or directory`, you don't have `python-dev` and/or `build-essential`.
* Make sure your nginx user owns the virtualenv (this should be guaranteed by the above instructions).

### nginx
* Don't forget to `systemctl reload nginx.service` if you make changes to the conf file.
* `nginx.conf.site` assumes the default `nginx.conf` file is being used. However, if it seems to not be working, copy `nginx.conf.webserver` from the repo to `/etc/nginx.nginx.conf`.

### MySQL server
* You will see really weird errors if you forgot the time zone step, and some user names will display improperly if you forgot to specify the character set.
* You can load the time zones at any time, and `ALTER DATABASE` to specify the character set at any time, but no promises about existing data quality.

### Settings and gunicorn
* Does `settings.ALLOWED_HOSTS` include your server's URL?
* Does `bin/gunicorn_start.sh` point at a virtualenv located in the correct place?
* If you used sudo to pip install requirements, gunicorn will fail; sudo will have installed outside the virtualenv and the files won't be available. You need to install as a user who has permissions to your virtualenv.
* Does `run/gunicorn.sock` exist, and does www-data have permissions on it? (If you get a `HaltServer: Worker failed to boot` error, this may be the cause.)

## Logs

Application log: `/var/www/html/TWLight/logs/twlight.log`
Gunicorn log: `/var/www/html/TWLight/logs/gunicorn.log`

Postfix and nginx log to their system defaults.

## Translations
The TWLight alpha ships with English, French, and Finnish. If you have translation files in a new language to deploy (yay!), or updates to an existing language file, see `locale/README.md`. This covers translations of all content in `.html` and `.py` files.

If you would like to translate *model instance content* (for instance, `Partner.description`), this uses the django-modeltranslation app. See https://django-modeltranslation.readthedocs.io/ for documentation; see `TWLight/resources/translation.py` for an example.
