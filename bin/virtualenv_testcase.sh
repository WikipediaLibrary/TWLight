#!/usr/bin/env bash
#
# Runs a specific set of Django tests, rather than all of them

if [  -z "$1" ]; then
    echo "Please specify a test case."
    exit 1
fi

{
    # Load virtual environment
    if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
    then
        DJANGO_LOG_LEVEL=CRITICAL DJANGO_SETTINGS_MODULE=TWLight.settings.local coverage run --source TWLight manage.py test --parallel --keepdb --noinput --timing $1
    else
        exit 1
    fi
} 2>&1
