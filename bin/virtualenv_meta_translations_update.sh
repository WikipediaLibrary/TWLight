#!/usr/bin/env bash
#
# Grabs short and long description translations from Meta and inserts them into the database via the meta_translations management command.

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    python manage.py meta_translations
else
    exit 1
fi
