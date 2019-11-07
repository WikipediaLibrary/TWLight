#!/usr/bin/env bash
#
# Sends coordinator reminder emails via the send_coordinator_reminders management command.

# Load virtual environment
if source ${TWLIGHT_HOME}/bin/virtualenv_activate.sh
then
    python3 manage.py send_coordinator_reminders --app_status PENDING
else
    exit 1
fi
