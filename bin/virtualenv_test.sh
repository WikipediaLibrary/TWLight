#!/usr/bin/env bash
#
# Runs Django tests (https://docs.djangoproject.com/en/1.11/topics/testing/)

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

{
    # print the date for logging purposes
    echo [$(date)]

    # Load virtual environment
    if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
    then
        # Run test suite via coverage so we can get a report without having to run separate tests for it.
        DJANGO_LOG_LEVEL=CRITICAL DJANGO_SETTINGS_MODULE=TWLight.settings.local coverage run --source TWLight manage.py test --keepdb --noinput
    else
        exit 1
    fi
} 2>&1
