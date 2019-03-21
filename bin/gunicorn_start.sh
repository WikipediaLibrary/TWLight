#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

if [ "$TWLIGHT_ENV" == "local" ]
then
    localopts="--reload --log-level=debug"
fi

name="twlight"
django_wsgi_module=TWLight.wsgi
# This is configurable: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
num_workers=3
timeout=300

cd $TWLIGHT_HOME
# Find gunicorn in the virtualenv
source "bin/virtualenv_activate.sh"
export PYTHONPATH=$TWLIGHT_HOME:$PYTHONPATH
export PATH=${PATH}:/opt/pandoc-2.7.1/bin

# Create the run directory if it doesn't exist
rundir=$(dirname $sockfile)
test -d $rundir || mkdir -p $rundir

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec gunicorn ${django_wsgi_module}:application \
  --name $name \
  --user $TWLIGHT_UNIXNAME \
  --workers $num_workers \
  --timeout $timeout \
  --bind=-0.0.0.0:80 \
  ${localopts} \

