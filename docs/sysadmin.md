# Sysadmin docs

This documentation is aimed at the system administrator who is setting up an
instance of TWLight in the Wikimedia Cloud VPS environment, where the production site is currently hosted.

## Access

To follow the rest of this guide you must first be a project administrator for the [twl project](https://tools.wmflabs.org/openstack-browser/project/twl). Contact an existing administrator if you require access.

## Process

### Horizon instance

For general information on using Horizon see the [Horizon FAQ](https://wikitech.wikimedia.org/wiki/Help:Horizon_FAQ).

1. If you are recreating an instance, first delete the old one in the Compute > Instances tab, taking note of the previous name.
2. Launch a new instance, entering the desired hostname (e.g. `twlight-staging`), and creating an `m1.medium` instance on `debian-8.11-jessie`.
3. Click on the new instance, and scroll to the bottom of the Puppet Configuration tab. Edit the Hiera Config to contain only `mount_nfs: true` to give this instance access to the project NFS share.
4. Create a web proxy by navigating to the DNS > Web Proxies tab and creating a new proxy to the newly created backend instance. The backend port should be set to 443.

### Connect

If this is your first time connecting to a Wikimedia Cloud Services environment, see [Help:Access](https://wikitech.wikimedia.org/wiki/Help:Access) for guidance on setting up SSH keys and config.

You should now be able to SSH to the instance with `ssh hostname.twl.eqiad.wmflabs`, replacing `hostname` as appropriate. If you are recreating an instance you may need to drop your old keys.

The instance should have access to `/data/project` (the NFS share), in which you can find the setup script `init.sh`. If this is missing for any reason, it can be restored from [this gist](https://gist.github.com/jsnshrmn/02493eb679427932174eff14faa66b67). The script makes local data directories, links to the NFS share, installs relevant modules and applies them.

This script automatically loads the appropriate .yaml configuration file from `/data/project/puppet/data/nodes/`. If you're using a hostname which isn't listed there you will need to create a new one. If recreating an instance, such as twlight-prod or twlight-staging, a config should already be present and the script will automatically detect it.

Once the script has finished running you should now be able to access the tool at the hostname you set up for the web proxy!

## To deploy updated code
TODO: Overview of Travis CI process, automatic updates, code update script.

Once updates have been git pushed from their local development environment to the repo, ssh into the server and 

## Background info & troubleshooting

### After Wikimedia server trouble
* Check permissions on everything (including the virtualenv) - they may not be what you expect.
* If you see `OperationalError: (2006, 'MySQL server has gone away')`, restarting gunicorn may fix this. (You'll see this if there's a timeout error, e.g. because gunicorn comes up before mysql is ready during reboot.)

### nginx
* Don't forget to `systemctl reload nginx.service` if you make changes to the conf file.
* `nginx.conf.site` assumes the default `nginx.conf` file is being used. However, if it seems to not be working, copy `conf/nginx.conf.webserver` from the repo to `/etc/nginx/nginx.conf`.

### Settings and gunicorn
* Does `settings.ALLOWED_HOSTS` include your server's domain?
* Does `bin/gunicorn_start.sh` point at a virtualenv located in the correct place?
* If you used sudo to pip install requirements, gunicorn will fail; sudo will have installed outside the virtualenv and the files won't be available. You need to install as a user who has permissions to your virtualenv.
* Does `run/gunicorn.sock` exist, and does www have permissions on it? (If you get a `HaltServer: Worker failed to boot` error, this may be the cause.)
* Does `/var/www/html/TWLight/TWLight/logs/gunicorn.log` exist, and does www have rwx permissions on it? (If you see an https 500 error, or if `/var/log/gunicorn.log` complains about permissions errors on the TWLight gunicorn log file, this is why.)
* Does your `bin/gunicorn_start.sh` use the appropriate DJANGO_SETTINGS_MODULE ? If it doesn't, you'll see an nginx default `Bad Request (400)`. 

### Partner pages or partner admin pages not rendering
* Did you just add a new language to the site, and forget to run `python manage.py makemigrations` on the server?

## Logs

TODO: Update

Application log: `/var/www/html/TWLight/logs/twlight.log`
Gunicorn log: `/var/www/html/TWLight/logs/gunicorn.log`
    * Note that this is the log *for the gunicorn process*, as distinct from *the service that starts gunicorn*.

Postfix, nginx, and the service that starts gunicorn on boot log to their system defaults in `/var/log`.

## Translations
TODO: Rewrite
