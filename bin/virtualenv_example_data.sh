#!/usr/bin/env bash
#
# Generates example data for local development of TWLight. Log in to an account you want to be a superuser first.

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    echo "Creating user data"
    python manage.py user_example_data 200 || exit

    echo "Creating resource data"
    python manage.py loaddata TWLight/resources/fixtures/partners/*.yaml
    python manage.py loaddata TWLight/resources/fixtures/streams/*.yaml
    python manage.py resources_example_data || exit

    echo "Creating applications data"
    python manage.py applications_example_data 1000 || exit
else
    exit 1
fi
