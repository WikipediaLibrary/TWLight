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
        python manage.py test $1
    else
        exit 1
    fi
} 2>&1
