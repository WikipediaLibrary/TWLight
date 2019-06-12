#!/usr/bin/env bash

# Environment variables should be be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

if [ "${TWLIGHT_ENV}" = "production" ]
then
    reminder_cmd="${TWLIGHT_HOME}/bin/./virtualenv_send_coordinator_reminders.sh"
    failure_cmd="${TWLIGHT_HOME}/bin/./twlight_failure.sh"

    # Send weekly reminders to coordinators.
    sudo su ${TWLIGHT_UNIXNAME}  bash -c "${reminder_cmd}" || ${failure_cmd} "${reminder_cmd}"
fi
