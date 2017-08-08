#!/bin/bash

NAME="twlight"
DJANGODIR=/var/www/html/TWLight/
SOCKFILE=/var/www/html/TWLight/run/gunicorn.sock
DJANGO_SETTINGS_MODULE=TWLight.settings.production
DJANGO_WSGI_MODULE=TWLight.wsgi
USER=www
# This is configurable: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
NUM_WORKERS=3

cd $DJANGODIR
# Find gunicorn in the virtualenv
source '/home/www/TWLight/bin/activate'
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --user $USER \
  --workers $NUM_WORKERS \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=/var/www/html/TWLight/TWLight/logs/gunicorn.log
