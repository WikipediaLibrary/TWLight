#!/usr/bin/env bash

if [ -z "$1" ]; then
    exit 1;
fi

failed_cmd="$1"

# Environment variables should be loaded under all conditions.
if [ -z "${TWLIGHT_HOME}" ]
then
    exit 1
fi

# Report failed command via email.
echo "$failed_cmd failed. Please check the logs." | mail -a "From: Wikipedia Library Card Platform <noreply@wikipedialibrary.wmflabs.org>" -s "task failed for $(hostname -f)" ${TWLIGHT_ERROR_MAILTO}
