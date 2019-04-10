#!/usr/bin/env bash

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

update="${TWLIGHT_HOME}/bin/./twlight_update_code.sh"

if failure=$( ! ${update} ) && [ -n "${TWLIGHT_ERROR_MAILTO+isset}" ]
then
    echo ${failure} | mail -a "From: Wikipedia Library Card Platform <noreply@wikipedialibrary.wmflabs.org>" -s "${update} failed for $(hostname -f)" ${TWLIGHT_ERROR_MAILTO}
fi
