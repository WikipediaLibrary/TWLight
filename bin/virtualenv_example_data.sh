#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    echo "Creating user data"
    python manage.py user_example_data 200 || exit

    echo "Creating resource data"
    python manage.py resources_example_data 50 || exit

    echo "Creating applications data"
    python manage.py applications_example_data 1000 || exit
else
    exit 1
fi
