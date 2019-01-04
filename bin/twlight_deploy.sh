#!/usr/bin/env bash

# Environment variables may not be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    source /etc/environment
fi

update="${TWLIGHT_HOME}/bin/./twlight_update_code.sh"

if failure=$( ! ${update} ) && [ -n "${TWLIGHT_ERROR_MAILTO+isset}" ]
then
    echo ${failure} | mail -s "${update} failed for $(hostname -f)" ${TWLIGHT_ERROR_MAILTO}
fi
