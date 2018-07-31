#!/usr/bin/env bash

NAME="twlight"
SOCKFILE=${TWLIGHT_HOME}/run/gunicorn.sock
DJANGO_WSGI_MODULE=TWLight.wsgi
# This is configurable: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
NUM_WORKERS=3
TIMEOUT=300

cd $TWLIGHT_HOME
# Find gunicorn in the virtualenv
source "/home/${TWLIGHT_UNIXNAME}/TWLight/bin/activate"
export PYTHONPATH=$TWLIGHT_HOME:$PYTHONPATH

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --user $TWLIGHT_UNIXNAME \
  --workers $NUM_WORKERS \
  --timeout $TIMEOUT \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=/var/www/html/TWLight/TWLight/logs/gunicorn.log
