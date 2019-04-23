#!/usr/bin/env bash
#
# Sends notices to users with authorizations that are soon to expire.

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    echo "Sending user emails"
    python manage.py user_renewal_notice || exit
else
    exit 1
fi
