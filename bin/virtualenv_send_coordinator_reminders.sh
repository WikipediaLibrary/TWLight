#!/usr/bin/env bash
#
# Sends coordinator reminder emails via the send_coordinator_reminders management command.

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh

python manage.py send_coordinator_reminders --app_status PENDING
