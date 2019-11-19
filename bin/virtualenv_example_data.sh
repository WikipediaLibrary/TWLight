#!/usr/bin/env bash
#
# Generates example data for local development of TWLight. Log in to an account you want to be a superuser first.

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    echo "Creating user data"
    python3 manage.py user_example_data 200 || exit

    echo "Creating resource data"
    python3 manage.py resources_example_data 50 || exit

    echo "Creating applications data"
    python3 manage.py applications_example_data 1000 || exit
else
    exit 1
fi
