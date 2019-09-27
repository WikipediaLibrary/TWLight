#!/usr/bin/env bash
#
# Un-waitlists proxy partners having atleast one available account. Doesn't work for partners with streams.

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    echo "Probing for waitlisted partners with atleast one available account"
    python manage.py proxy_waitlist_disable || exit
else
    exit 1
fi
